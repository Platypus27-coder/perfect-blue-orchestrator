import os
import json
import hmac
import html
import random
import re
import requests
import subprocess
import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import google.generativeai as genai

try:
    from backend.security import (
        WorkspaceSecurityError,
        ensure_workspace_read_allowed,
        env_flag,
        resolve_workspace_path,
        sanitize_subprocess_environment,
    )
    from backend.storage import RuntimeStore
except ImportError:
    from security import (
        WorkspaceSecurityError,
        ensure_workspace_read_allowed,
        env_flag,
        resolve_workspace_path,
        sanitize_subprocess_environment,
    )
    from storage import RuntimeStore

# Đọc cấu hình từ file .env cục bộ (tránh lộ Key lên GitHub)
env_path = ".env"
if not os.path.exists(env_path) and os.path.exists("../.env"):
    env_path = "../.env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                key, val = line.strip().split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = Path(
    os.environ.get("PERFECTBLUE_STATE_DIR", str(WORKSPACE_DIR / ".perfectblue"))
).resolve()
STORE = RuntimeStore(STATE_DIR / "perfectblue.db")
RUNTIME_TOKEN = os.environ.get("PERFECTBLUE_RUNTIME_TOKEN", "").strip()
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:3000,http://127.0.0.1:3000"
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("PERFECTBLUE_CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app = FastAPI(title="PerfectBlue AI Runtime", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-PerfectBlue-Token"],
)


@app.middleware("http")
async def require_runtime_token(request: Request, call_next):
    """Protect mutating/runtime routes when an operator configures a token."""

    if not RUNTIME_TOKEN or request.method == "OPTIONS" or request.url.path == "/health":
        return await call_next(request)

    authorization = request.headers.get("authorization", "")
    bearer_token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    supplied_token = bearer_token or request.headers.get("x-perfectblue-token", "").strip()
    if not supplied_token or not hmac.compare_digest(supplied_token, RUNTIME_TOKEN):
        return JSONResponse(
            status_code=401,
            content={"error": "PerfectBlue runtime token required."},
        )
    return await call_next(request)

# Khởi tạo danh sách các khóa Gemini để xoay tua
GEMINI_KEYS_POOL = []
keys_str = os.environ.get("GEMINI_API_KEYS", "")
if keys_str:
    GEMINI_KEYS_POOL.extend([k.strip() for k in keys_str.split(",") if k.strip()])

single_key = os.environ.get("GEMINI_API_KEY", "")
if single_key and single_key not in GEMINI_KEYS_POOL:
    GEMINI_KEYS_POOL.append(single_key.strip())

if GEMINI_KEYS_POOL:
    genai.configure(api_key=GEMINI_KEYS_POOL[0])


# --- Giai đoạn 4: Tích hợp Kỹ năng Thực thi (Tools from Public APIs) ---

def get_weather(location: str) -> str:
    """Lấy thông tin thời tiết hiện tại của một địa điểm cụ thể.
    
    Args:
        location: Tên thành phố và quốc gia (Ví dụ: Hanoi, Vietnam hoặc Tokyo, Japan).
    """
    try:
        url = f"https://wttr.in/{location}?format=3"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return f"Thời tiết tại {location}: {res.text.strip()}"
        return f"Không thể lấy thời tiết cho {location}."
    except Exception as e:
        return f"Lỗi gọi API thời tiết: {str(e)}"

def get_crypto_price(coin_id: str) -> str:
    """Lấy giá hiện tại của một đồng tiền điện tử (crypto) bằng USD từ CoinGecko.
    
    Args:
        coin_id: ID viết thường của đồng coin (Ví dụ: bitcoin, ethereum, solana).
    """
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            price = data.get(coin_id, {}).get("usd")
            if price:
                return f"Giá hiện tại của {coin_id.upper()} là ${price:,} USD."
            return f"Không tìm thấy thông tin giá của đồng coin '{coin_id}'."
        return "Lỗi kết nối API CoinGecko."
    except Exception as e:
        return f"Lỗi gọi API tỷ giá coin: {str(e)}"

def search_wikipedia(query: str) -> str:
    """Tìm kiếm nhanh thông tin tóm tắt trên Wikipedia tiếng Anh về một chủ đề.
    
    Args:
        query: Từ khóa hoặc chủ đề cần tìm kiếm (Ví dụ: Artificial Intelligence, Python programming).
    """
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            search_results = data.get("query", {}).get("search", [])
            if search_results:
                snippets = []
                for idx, item in enumerate(search_results[:3]):
                    title = item.get("title")
                    snippet = item.get("snippet").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                    snippets.append(f"{idx+1}. {title}: {snippet}...")
                return "Kết quả Wikipedia tìm được:\n" + "\n".join(snippets)
            return f"Không tìm thấy bài viết Wikipedia nào cho '{query}'."
        return "Lỗi kết nối Wikipedia API."
    except Exception as e:
        return f"Lỗi tìm kiếm Wikipedia: {str(e)}"

def get_my_location() -> str:
    """Lấy thông tin địa lý và địa chỉ IP hiện tại của server/máy tính chạy backend."""
    try:
        url = "http://ip-api.com/json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                return f"Địa điểm máy chủ: {data.get('city')}, {data.get('regionName')}, {data.get('country')} (IP: {data.get('query')})"
            return "Không thể phân tích địa chỉ IP."
        return "Lỗi kết nối API xác định vị trí."
    except Exception as e:
        return f"Lỗi gọi API vị trí: {str(e)}"

# --- VIP NATIVE TOOLS (PROPOSAL 1) ---
def get_alpha_vantage_stock_price(symbol: str) -> str:
    """Lấy dữ liệu giá cổ phiếu hiện tại (Real-time) từ Alpha Vantage.
    
    Args:
        symbol: Mã cổ phiếu (Ví dụ: AAPL, TSLA, MSFT).
    """
    key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not key: return "Lỗi: Chưa cấu hình ALPHAVANTAGE_API_KEY."
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={key}"
        res = requests.get(url, timeout=10).json()
        quote = res.get("Global Quote", {})
        if quote:
            return f"Cổ phiếu {symbol}: Giá hiện tại ${quote.get('05. price')}, Thay đổi: {quote.get('09. change')} ({quote.get('10. change percent')})"
        return f"Không tìm thấy dữ liệu cho {symbol}. (Lưu ý: Alpha Vantage giới hạn 25 requests/ngày cho tài khoản free)"
    except Exception as e: return str(e)

def get_news_from_newsapi(query: str) -> str:
    """Tìm kiếm các bài báo và tin tức nóng hổi trên toàn cầu từ NewsAPI.
    
    Args:
        query: Chủ đề tìm kiếm (Ví dụ: AI, Technology, Bitcoin).
    """
    key = os.environ.get("NEWS_API_KEY")
    if not key: return "Lỗi: Chưa cấu hình NEWS_API_KEY."
    try:
        url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={key}"
        res = requests.get(url, timeout=10).json()
        if res.get("status") == "ok":
            articles = res.get("articles", [])[:3]
            out = f"Tin tức về '{query}':\n"
            for a in articles: out += f"- {a.get('title')} ({a.get('source', {}).get('name')})\n"
            return out if articles else "Không có tin tức nào mới."
        return "Lỗi từ NewsAPI."
    except Exception as e: return str(e)

def get_openweathermap_weather(city: str) -> str:
    """Lấy thời tiết chính xác cực cao từ OpenWeatherMap.
    
    Args:
        city: Tên thành phố (Ví dụ: Hanoi, London).
    """
    key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not key: return "Lỗi: Chưa cấu hình OPENWEATHERMAP_API_KEY."
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric"
        res = requests.get(url, timeout=10).json()
        if res.get("cod") == 200:
            return f"Thời tiết tại {city}: Nhiệt độ {res['main']['temp']}°C, {res['weather'][0]['description']}, Độ ẩm: {res['main']['humidity']}%"
        return "Không tìm thấy thành phố."
    except Exception as e: return str(e)

def create_visual_chart_html(filename: str, title: str, chart_type: str, labels_comma_separated: str, data_comma_separated: str) -> str:
    """Tạo một file HTML chứa biểu đồ đồ họa đẹp mắt (Chart.js) để người dùng xem trực quan.
    
    Args:
        filename: Tên file HTML để lưu (Ví dụ: chart.html).
        title: Tiêu đề biểu đồ.
        chart_type: Loại biểu đồ (bar, line, pie, doughnut).
        labels_comma_separated: Các nhãn cách nhau bằng dấu phẩy (Ví dụ: Jan,Feb,Mar).
        data_comma_separated: Các số liệu cách nhau bằng dấu phẩy (Ví dụ: 10,20,30).
    """
    try:
        normalized_type = chart_type.strip().lower()
        if normalized_type not in {"bar", "line", "pie", "doughnut"}:
            return "Lỗi: Loại biểu đồ phải là bar, line, pie hoặc doughnut."
        labels = [item.strip() for item in labels_comma_separated.split(",") if item.strip()]
        values = [float(item.strip()) for item in data_comma_separated.split(",") if item.strip()]
        if not labels or len(labels) != len(values):
            return "Lỗi: Số lượng nhãn và số liệu phải bằng nhau và không được trống."
        safe_title_json = json.dumps(title, ensure_ascii=False).replace("<", "\\u003c")
        labels_json = json.dumps(labels, ensure_ascii=False).replace("<", "\\u003c")
        values_json = json.dumps(values)
        html_content = f'''<!DOCTYPE html><html><head><title>{html.escape(title)}</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>body{{font-family:sans-serif;background:#1e1e1e;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}} .container{{width:80%;max-width:800px;background:#2d2d2d;padding:20px;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.5);}}</style></head><body><div class="container"><canvas id="myChart"></canvas></div><script>
    new Chart(document.getElementById('myChart'), {{
        type: {json.dumps(normalized_type)},
        data: {{
            labels: {labels_json},
            datasets: [{{ label: {safe_title_json}, data: {values_json}, backgroundColor: ['#ff6384','#36a2eb','#ffce56','#4bc0c0','#9966ff','#ff9f40'], borderColor: '#fff', borderWidth: 1 }}]
        }},
        options: {{ responsive: true }}
    }});
    </script></body></html>'''
        path = resolve_workspace_path(WORKSPACE_DIR, filename, require_project_path=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write(html_content)
        return f"Đã tạo biểu đồ thành công tại {filename}. Hãy bảo người dùng mở file này trên trình duyệt để xem!"
    except (ValueError, WorkspaceSecurityError) as e:
        return f"Lỗi: {str(e)}"
    except Exception as e:
        return f"Lỗi tạo biểu đồ: {str(e)}"

def delegate_task_to_agent(target_agent: str, instructions: str) -> str:
    """Giao việc cho một Agent khác trong văn phòng và chờ nhận kết quả báo cáo.
    Dùng công cụ này khi bạn cần chuyên môn của bộ phận khác (Ví dụ: Programmer cần QA test, Manager cần Designer thiết kế).
    
    Args:
        target_agent: Tên agent nhận việc (programmer, qa, designer, manager, researcher, writer, support, devops, security).
        instructions: Lời nhắn/yêu cầu công việc chi tiết. Dặn dò rõ những gì cần làm.
    """
    system_inst = AGENT_PERSONAS.get(target_agent, AGENT_PERSONAS["default"])
    safe_tools = [t for t in PUBLIC_TOOLS if t.__name__ not in ["delegate_task_to_agent", "recruit_expert_and_delegate_task"]]
    
    try:
        if GEMINI_KEYS_POOL:
            genai.configure(api_key=random.choice(GEMINI_KEYS_POOL))
        model = genai.GenerativeModel(
            model_name=active_agent_models().get(target_agent, DEFAULT_AGENT_MODEL),
            system_instruction=system_inst,
            tools=safe_tools
        )
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(instructions)
        return f"[BÁO CÁO TỪ {target_agent.upper()}]:\n{response.text}"
    except Exception as e:
        return f"Lỗi khi giao việc cho {target_agent}: {str(e)}"

def recruit_expert_and_delegate_task(expert_title: str, expert_system_prompt: str, instructions: str) -> str:
    """Tự động tuyển dụng (khởi tạo) một Agent Chuyên gia mới hoàn toàn với chuyên môn tùy ý, giao việc cho họ và chờ kết quả.
    Công cụ mạnh mẽ nhất dành cho Quản lý khi cần một vai trò không có sẵn trong văn phòng (Ví dụ: Luật sư, Chuyên gia Marketing, Kế toán).
    
    Args:
        expert_title: Chức danh của chuyên gia (Ví dụ: Luật sư trưởng, Giám đốc Marketing).
        expert_system_prompt: Mô tả cực kỳ chi tiết về tính cách, chuyên môn, và cách hành xử của chuyên gia này (Ví dụ: Bạn là một Luật sư 20 năm kinh nghiệm...).
        instructions: Lời nhắn/yêu cầu công việc chi tiết muốn giao cho chuyên gia này.
    """
    # Bỏ chính tool này và tool delegate cũ ra khỏi danh sách để tránh đẻ đệ quy vô hạn
    safe_tools = [t for t in PUBLIC_TOOLS if t.__name__ not in ["delegate_task_to_agent", "recruit_expert_and_delegate_task"]]
    
    try:
        if GEMINI_KEYS_POOL:
            genai.configure(api_key=random.choice(GEMINI_KEYS_POOL))
        model = genai.GenerativeModel(
            model_name=DEFAULT_AGENT_MODEL,
            system_instruction=expert_system_prompt,
            tools=safe_tools
        )
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(instructions)
        return f"[BÁO CÁO TỪ CHUYÊN GIA MỚI TUYỂN DỤNG - {expert_title.upper()}]:\n{response.text}"
    except Exception as e:
        return f"Lỗi khi tuyển dụng và giao việc cho {expert_title}: {str(e)}"

def read_workspace_file(relative_path: str) -> str:
    """Đọc nội dung của một tệp tin trong thư mục dự án (workspace).
    
    Args:
        relative_path: Đường dẫn tương đối từ gốc dự án (Ví dụ: 'README.md' hoặc 'backend/main.py').
    """
    try:
        safe_path = resolve_workspace_path(WORKSPACE_DIR, relative_path)
        ensure_workspace_read_allowed(WORKSPACE_DIR, safe_path)
        if not safe_path.exists() or not safe_path.is_file():
            return f"Lỗi: Tệp '{relative_path}' không tồn tại."
        if safe_path.stat().st_size > 1_000_000:
            return "Lỗi: Chỉ được đọc tệp văn bản nhỏ hơn 1 MB."
        with safe_path.open("r", encoding="utf-8") as f:
            return f.read()
    except WorkspaceSecurityError as e:
        return f"Lỗi: {str(e)}"
    except Exception as e:
        return f"Lỗi đọc tệp: {str(e)}"

def write_workspace_file(relative_path: str, content: str) -> str:
    """Ghi hoặc cập nhật nội dung của một tệp tin trong thư mục dự án (workspace).
    
    Args:
        relative_path: Đường dẫn tương đối từ gốc dự án (Ví dụ: 'docs/architecture.md' hoặc 'backend/test_script.py').
        content: Nội dung văn bản cần ghi vào tệp.
    """
    try:
        if len(content.encode("utf-8")) > 2_000_000:
            return "Lỗi: Nội dung tệp vượt quá giới hạn 2 MB."
        safe_path = resolve_workspace_path(
            WORKSPACE_DIR, relative_path, require_project_path=True
        )
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with safe_path.open("w", encoding="utf-8") as f:
            f.write(content)
        return f"Thành công: Đã tạo/ghi nội dung vào tệp '{relative_path}'."
    except WorkspaceSecurityError as e:
        return f"Lỗi: {str(e)}"
    except Exception as e:
        return f"Lỗi ghi tệp: {str(e)}"

def execute_python_code(code: str) -> str:
    """Chạy Python cục bộ khi operator đã chủ động bật công cụ nguy hiểm này.

    Đây không phải container sandbox. Công cụ bị tắt mặc định và chỉ nên bật
    trong môi trường local đáng tin cậy.
    
    Args:
        code: Đoạn code Python hoàn chỉnh cần thực thi.
    """
    if not env_flag("PERFECTBLUE_ENABLE_PYTHON_TOOL"):
        return (
            "Công cụ chạy Python đang bị tắt vì lý do an toàn. "
            "Operator có thể bật bằng PERFECTBLUE_ENABLE_PYTHON_TOOL=true."
        )
    if len(code) > 20_000:
        return "Lỗi: Mã Python vượt quá giới hạn 20.000 ký tự."
    try:
        sandbox_dir = WORKSPACE_DIR / "projects" / ".runtime-sandbox"
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=sandbox_dir,
            env=sanitize_subprocess_environment(),
        )
        output = ""
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout[:20_000]}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr[:20_000]}\n"
        if not output:
            output = "Chạy thành công (Không có đầu ra console)."
        return output
    except subprocess.TimeoutExpired:
        return "Lỗi: Thời gian chạy vượt quá giới hạn (Timeout 10 giây)."
    except Exception as e:
        return f"Lỗi thực thi: {str(e)}"

def manage_project_tasks(action: str, task_id: int = None, title: str = "", description: str = "", status: str = "todo") -> str:
    """Quản lý danh sách công việc (Tasks) của dự án. Hỗ trợ liệt kê, tạo mới, cập nhật hoặc xóa task.
    
    Args:
        action: Hành động cần làm ('list', 'create', 'update', 'delete').
        task_id: ID số nguyên của task (Cần cho hành động 'update' và 'delete').
        title: Tiêu đề công việc (Cần khi 'create').
        description: Mô tả công việc chi tiết.
        status: Trạng thái ('todo', 'in_progress', 'done').
    """
    normalized_action = action.strip().lower()
    allowed_statuses = {"todo", "in_progress", "review", "done", "failed"}
    if status not in allowed_statuses:
        return "Lỗi: Trạng thái phải là todo, in_progress, review, done hoặc failed."

    if normalized_action == "list":
        tasks = STORE.list_tasks()
        if not tasks:
            return "Danh sách công việc đang trống. Hãy tạo công việc đầu tiên!"
        res = "Danh sách công việc dự án:\n"
        for t in tasks:
            res += f"- ID [{t.get('id')}] | Trạng thái: [{t.get('status').upper()}] | Tiêu đề: {t.get('title')} ({t.get('description')})\n"
        return res
        
    elif normalized_action == "create":
        if not title.strip():
            return "Lỗi: Tiêu đề công việc không được để trống."
        new_task = STORE.create_task(title.strip(), description.strip(), status)
        return f"Thành công: Đã tạo công việc ID {new_task['id']} - '{title.strip()}'."
        
    elif normalized_action == "update":
        if not task_id:
            return "Lỗi: Thiếu tham số task_id để cập nhật."
        updates = {"status": status}
        if title:
            updates["title"] = title.strip()
        if description:
            updates["description"] = description.strip()
        if STORE.update_task(task_id, updates):
            return f"Thành công: Đã cập nhật công việc ID {task_id}."
        return f"Lỗi: Không tìm thấy công việc ID {task_id}."
        
    elif normalized_action == "delete":
        if not task_id:
            return "Lỗi: Thiếu tham số task_id để xóa."
        if STORE.delete_task(task_id):
            return f"Thành công: Đã xóa công việc ID {task_id}."
        return f"Lỗi: Không tìm thấy công việc ID {task_id}."
        
    return "Lỗi: Hành động không hợp lệ. Chọn 'list', 'create', 'update', hoặc 'delete'."

def get_latest_hacker_news() -> str:
    """Lấy danh sách 5 bài viết/tin tức công nghệ hàng đầu đang thịnh hành từ Hacker News."""
    try:
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            ids = res.json()[:5]
            stories = []
            for story_id in ids:
                s_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5)
                if s_res.status_code == 200:
                    s_data = s_res.json()
                    stories.append(f"- {s_data.get('title')} ({s_data.get('url', 'Không có liên kết')})")
            return "Top 5 tin công nghệ thịnh hành trên Hacker News:\n" + "\n".join(stories)
        return "Lỗi: Không thể lấy danh sách tin Hacker News."
    except Exception as e:
        return f"Lỗi gọi API Hacker News: {str(e)}"

def get_github_repo_details(repo: str) -> str:
    """Lấy thông tin tổng quan của một Repository công khai bất kỳ trên GitHub.
    
    Args:
        repo: Tên repo dạng 'owner/name' (Ví dụ: 'google/generative-ai-python' hoặc 'tensorflow/tensorflow').
    """
    try:
        url = f"https://api.github.com/repos/{repo}"
        res = requests.get(url, headers={"User-Agent": "PerfectBlue-App"}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return (
                f"Thông tin Repo '{repo}':\n"
                f"- Mô tả: {data.get('description', 'Không có mô tả.')}\n"
                f"- Sao (Stars): {data.get('stargazers_count')} | Forks: {data.get('forks_count')}\n"
                f"- Issues đang mở: {data.get('open_issues_count')}\n"
                f"- Ngôn ngữ chính: {data.get('language')}"
            )
        return f"Lỗi: Không tìm thấy Repo '{repo}' hoặc vượt giới hạn API rate limit."
    except Exception as e:
        return f"Lỗi truy vấn GitHub: {str(e)}"

def search_public_apis_database(category: str = "", keyword: str = "") -> str:
    """Tìm kiếm các API miễn phí trong cơ sở dữ liệu public-apis cục bộ (hơn 1400+ API).
    Trả về danh sách các API phù hợp bao gồm: Tên API, URL liên kết, mô tả, yêu cầu xác thực (Auth), HTTPS và CORS.
    
    Args:
        category: Danh mục API muốn tìm (Ví dụ: Animals, Anime, Books, Cryptocurrency, Finance, Geocoding, Music, News, Security, Weather, v.v.).
        keyword: Từ khóa tìm kiếm xuất hiện trong tên hoặc mô tả của API.
    """
    readme_path = os.path.join(WORKSPACE_DIR, "public-apis", "README.md")
    if not os.path.exists(readme_path):
        return "Lỗi: Không tìm thấy cơ sở dữ liệu public-apis cục bộ. Hãy clone repo public-apis vào gốc dự án."
    
    results = []
    current_category = ""
    
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith("### "):
                    current_category = line_str.replace("### ", "").strip()
                    continue
                
                # Kiểm tra xem dòng có phải là dòng trong bảng API không (bắt đầu và kết thúc bằng |)
                if line_str.startswith("|") and line_str.endswith("|"):
                    # Bỏ qua dòng tiêu đề bảng và dòng phân cách
                    if "Description" in line_str or ":---" in line_str or "---:" in line_str:
                        continue
                    
                    parts = [p.strip() for p in line_str.split("|")[1:-1]]
                    if len(parts) >= 2:
                        api_part = parts[0]  # Ví dụ: [AdoptAPet](https://...)
                        desc = parts[1]
                        auth = parts[2] if len(parts) > 2 else "No"
                        https = parts[3] if len(parts) > 3 else "Unknown"
                        cors = parts[4] if len(parts) > 4 else "Unknown"
                        
                        # Trích xuất tên API và URL
                        api_name = api_part
                        api_url = ""
                        if "[" in api_part and "]" in api_part and "(" in api_part and ")" in api_part:
                            try:
                                api_name = api_part.split("]")[0].replace("[", "").strip()
                                api_url = api_part.split("](")[1].split(")")[0].strip()
                            except:
                                pass
                        
                        # Kiểm tra bộ lọc
                        category_match = not category or category.lower() in current_category.lower()
                        keyword_match = not keyword or (keyword.lower() in api_name.lower() or keyword.lower() in desc.lower())
                        
                        if category_match and keyword_match:
                            results.append({
                                "category": current_category,
                                "name": api_name,
                                "url": api_url,
                                "description": desc,
                                "auth": auth,
                                "https": https,
                                "cors": cors
                            })
                            if len(results) >= 15:  # Giới hạn 15 kết quả để tránh quá tải token
                                break
                                
        if not results:
            return "Không tìm thấy API nào khớp với tiêu chí của bạn."
            
        output = f"Đã tìm thấy {len(results)} API phù hợp trong cơ sở dữ liệu public-apis:\n"
        for idx, r in enumerate(results):
            output += (
                f"{idx+1}. [{r['name']}] ({r['url']})\n"
                f"   - Danh mục: {r['category']}\n"
                f"   - Mô tả: {r['description']}\n"
                f"   - Auth: {r['auth']} | HTTPS: {r['https']} | CORS: {r['cors']}\n"
            )
        return output
    except Exception as e:
        return f"Lỗi đọc dữ liệu public-apis: {str(e)}"

def get_public_api_categories() -> str:
    """Lấy danh sách tất cả các Danh mục (Categories) API có sẵn trong cơ sở dữ liệu public-apis cục bộ."""
    readme_path = os.path.join(WORKSPACE_DIR, "public-apis", "README.md")
    if not os.path.exists(readme_path):
        return "Lỗi: Không tìm thấy cơ sở dữ liệu public-apis cục bộ."
    
    categories = []
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith("### "):
                    cat = line_str.replace("### ", "").strip()
                    if cat and cat not in ["APILayer APIs", "Learn more about Public APIs", "Index"]:
                        categories.append(cat)
        return "Các danh mục API có sẵn:\n" + ", ".join(categories)
    except Exception as e:
        return f"Lỗi đọc danh mục public-apis: {str(e)}"

# Danh sách các tool công khai tích hợp cho Gemini
PUBLIC_TOOLS = [
    get_weather, 
    get_crypto_price, 
    search_wikipedia, 
    get_my_location,
    read_workspace_file,
    write_workspace_file,
    execute_python_code,
    manage_project_tasks,
    search_public_apis_database,
    get_public_api_categories,
    get_alpha_vantage_stock_price,
    get_news_from_newsapi,
    get_openweathermap_weather,
    create_visual_chart_html,
    delegate_task_to_agent,
    recruit_expert_and_delegate_task
]



# --- Giai đoạn 2: Quản lý Trí nhớ & Định danh (Memory & Personas) ---

# System prompts cực kỳ chi tiết cho 9 Agent trong văn phòng 3D
AGENT_PERSONAS = {
    "programmer": (
        "Bạn là Coder siêu hạng của văn phòng PerfectBlue. Bạn phụ trách lập trình backend và frontend. "
        "Khi trả lời, hãy đi thẳng vào vấn đề kỹ thuật, cung cấp mã nguồn tối ưu, ngắn gọn và chuẩn chỉ. "
        "Nếu được giao việc, hãy viết code rõ ràng và ghi chú những điểm cần lưu ý."
    ),
    "qa": (
        "Bạn là Kỹ sư Đảm bảo Chất lượng (QA Engineer) khó tính của PerfectBlue. "
        "Nhiệm vụ của bạn là kiểm tra, phát hiện lỗi (bugs), và phân tích các trường hợp biên (edge cases). "
        "Khi được gửi code hoặc tính năng, hãy phân tích kỹ các điểm yếu bảo mật, hiệu năng và gợi ý test cases."
    ),
    "designer": (
        "Bạn là Designer sáng tạo, chuyên gia UI/UX của PerfectBlue. "
        "Bạn luôn nghĩ về trải nghiệm người dùng, bảng màu, khoảng trắng, bố cục và hiệu ứng chuyển động. "
        "Hãy trả lời tinh tế, chú ý tính thẩm mỹ và đưa ra các hướng dẫn trực quan hóa tốt nhất."
    ),
    "manager": (
        "Bạn là Quản lý dự án (Project Manager) điều phối văn phòng PerfectBlue. "
        "Nhiệm vụ của bạn là quản lý tài nguyên, giao việc, phân tích tiến độ và báo cáo công việc. "
        "Hãy nói chuyện chuyên nghiệp, lịch sự, có tính tổ chức và định hướng giải quyết vấn đề."
    ),
    "researcher": (
        "Bạn là Nghiên cứu viên AI/ML (Researcher) của PerfectBlue. "
        "Bạn luôn cập nhật các xu hướng AI, bài báo khoa học và công nghệ mới. "
        "Hãy trả lời chi tiết, học thuật, có chiều sâu khoa học và cung cấp các phân tích so sánh công nghệ."
    ),
    "writer": (
        "Bạn là Biên soạn nội dung (Copywriter/Content Specialist) của PerfectBlue. "
        "Bạn chịu trách nhiệm viết tài liệu kỹ thuật, bài viết chuẩn SEO, email và tài liệu hướng dẫn. "
        "Hãy viết mượt mà, cấu trúc mạch lạc, hấp dẫn người đọc."
    ),
    "support": (
        "Bạn là Đại diện Chăm sóc Khách hàng (Customer Support) của PerfectBlue. "
        "Hãy trả lời vô cùng thân thiện, kiên nhẫn, ấm áp và luôn sẵn lòng hướng dẫn người dùng giải quyết khó khăn."
    ),
    "devops": (
        "Bạn là Kỹ sư DevOps của PerfectBlue. Bạn quản lý Docker, Kubernetes, CI/CD, hệ thống Cloud và Deploy. "
        "Hãy trả lời thực tế, tập trung vào kiến trúc hạ tầng, tính ổn định và tự động hóa hệ thống."
    ),
    "security": (
        "Bạn là Chuyên gia Bảo mật thông tin (Cybersecurity Specialist) của PerfectBlue. "
        "Nhiệm vụ của bạn là bảo vệ hệ thống khỏi các cuộc tấn công mạng, audit mã nguồn và thiết lập chính sách an toàn. "
        "Hãy trả lời cảnh giác, nêu bật các rủi ro bảo mật tiềm ẩn và cách khắc phục."
    ),
    "default": "Bạn là một Agent chuyên nghiệp trong văn phòng 3D PerfectBlue. Hãy hỗ trợ nhóm hoàn thành mục tiêu dự án."
}

SESSION_MEMORY = {}
DEFAULT_AGENT_MODEL = os.environ.get("PERFECTBLUE_DEFAULT_MODEL", "gemini-3.5-flash")
MODEL_REGISTRY = {
    "gemini-3.5-flash": {
        "speed": "fast",
        "cost": "free",
        "features": ["tools", "system_instructions"],
    },
    "gemini-3.1-pro": {
        "speed": "moderate",
        "cost": "free",
        "features": ["tools", "system_instructions"],
    },
}
DEFAULT_AGENT_ROLES = [
    "programmer",
    "qa",
    "designer",
    "manager",
    "researcher",
    "writer",
    "support",
    "devops",
    "security",
]
STORE.seed_agents(
    [
        {
            "id": role,
            "name": role.replace("_", " ").title(),
            "role": role,
            "description": AGENT_PERSONAS[role],
            "model": DEFAULT_AGENT_MODEL,
            "status": "online",
        }
        for role in DEFAULT_AGENT_ROLES
    ]
)
for stored_agent in STORE.list_agents():
    AGENT_PERSONAS.setdefault(
        stored_agent["id"],
        stored_agent.get("description") or AGENT_PERSONAS["default"],
    )


def list_active_agents():
    return STORE.list_agents()


def active_agent_models():
    return {agent["id"]: agent["model"] for agent in list_active_agents()}

def add_activity(agent_name: str, action: str, detail: str):
    STORE.add_activity(agent_name.capitalize(), action, detail)

@app.get("/api/v1/activities")
def get_activities(limit: int = 20):
    activities = STORE.list_activities(limit)
    return {
        "activities": [
            {
                **activity,
                "time": __import__("datetime").datetime.fromtimestamp(
                    activity["created_at"]
                ).strftime("%H:%M:%S"),
            }
            for activity in activities
        ]
    }

@app.get("/health")
def health():
    return {
        "ok": True,
        "status": "healthy - PerfectBlue Core Engine is active",
        "runtime": "perfectblue",
        "version": "0.2.0",
        "auth": "required" if RUNTIME_TOKEN else "local-only",
        "python_tool": "enabled" if env_flag("PERFECTBLUE_ENABLE_PYTHON_TOOL") else "disabled",
    }

@app.get("/state")
def state():
    agents = list_active_agents()
    return {
        "identity": {
            "name": "PerfectBlue Master Brain",
            "role": "orchestrator"
        },
        "runtime": {
            "name": "PerfectBlue Core",
            "version": "0.2.0",
            "vendor": "PerfectBlue",
            "active_model": DEFAULT_AGENT_MODEL,
            "status": "Running",
            "persistence": "sqlite",
        },
        "active": {agent["id"]: agent["model"] for agent in agents},
        "agents": agents,
    }

@app.post("/agents/add")
async def add_agent_endpoint(request: Request):
    data = await request.json()
    raw_id = str(data.get("id", data.get("role", "custom"))).strip().lower()
    role_id = re.sub(r"[^a-z0-9_-]+", "-", raw_id).strip("-")
    if not role_id or len(role_id) > 64:
        return JSONResponse(status_code=400, content={"error": "Agent id is invalid."})
    model = str(data.get("model", DEFAULT_AGENT_MODEL)).strip() or DEFAULT_AGENT_MODEL
    if model not in MODEL_REGISTRY:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unsupported model: {model}"},
        )
    role = str(data.get("role", role_id)).strip().lower() or role_id
    name = str(data.get("name", role_id.replace("_", " ").title())).strip()
    description = str(
        data.get("description", f"Bạn là một {role} chuyên nghiệp.")
    ).strip()
    agent = STORE.upsert_agent(
        {
            "id": role_id,
            "name": name[:80] or role_id.title(),
            "role": role[:64],
            "description": description[:4_000],
            "model": model,
            "status": "online",
        }
    )
    
    if role_id not in AGENT_PERSONAS:
        AGENT_PERSONAS[role_id] = description

    add_activity(role_id, "đã được cấu hình", f"Model: {model}")
    return {"ok": True, "agent": agent}


@app.delete("/agents/{agent_id}")
def delete_agent_endpoint(agent_id: str):
    normalized_id = agent_id.strip().lower()
    if normalized_id in DEFAULT_AGENT_ROLES:
        return JSONResponse(
            status_code=409,
            content={"error": "Default agents cannot be deleted."},
        )
    if not STORE.delete_agent(normalized_id):
        return JSONResponse(status_code=404, content={"error": "Agent not found."})
    AGENT_PERSONAS.pop(normalized_id, None)
    add_activity(normalized_id, "đã bị xóa", "Agent removed from the runtime")
    return {"ok": True}

@app.get("/registry")
def registry():
    return {"models": MODEL_REGISTRY}


@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    return {"session_id": session_id, "messages": STORE.list_session_messages(session_id)}


@app.get("/api/v1/tasks")
def list_tasks_endpoint():
    return {"tasks": STORE.list_tasks()}


@app.post("/api/v1/tasks")
async def create_task_endpoint(request: Request):
    data = await request.json()
    title = str(data.get("title", "")).strip()
    if not title:
        return JSONResponse(status_code=400, content={"error": "Task title is required."})
    status = str(data.get("status", "todo")).strip()
    if status not in {"todo", "in_progress", "review", "done", "failed"}:
        return JSONResponse(status_code=400, content={"error": "Task status is invalid."})
    task = STORE.create_task(
        title[:200],
        str(data.get("description", ""))[:4_000],
        status,
        str(data.get("assignee_id", "")).strip() or None,
    )
    return {"ok": True, "task": task}


@app.post("/api/v1/tasks/{task_id}")
async def update_task_endpoint(task_id: int, request: Request):
    data = await request.json()
    updates = {
        key: value
        for key, value in data.items()
        if key in {"title", "description", "status", "assignee_id"}
    }
    if "status" in updates and updates["status"] not in {
        "todo",
        "in_progress",
        "review",
        "done",
        "failed",
    }:
        return JSONResponse(status_code=400, content={"error": "Task status is invalid."})
    if not STORE.update_task(task_id, updates):
        return JSONResponse(status_code=404, content={"error": "Task not found."})
    return {"ok": True}


@app.delete("/api/v1/tasks/{task_id}")
def delete_task_endpoint(task_id: int):
    if not STORE.delete_task(task_id):
        return JSONResponse(status_code=404, content={"error": "Task not found."})
    return {"ok": True}


# --- Giai đoạn 1 & 4: LLM Engine & Định tuyến lệnh (Routing) & Thực thi Tools ---
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        data = await request.json()
        raw_messages = data.get("messages", [])
        if not isinstance(raw_messages, list) or len(raw_messages) > 100:
            return JSONResponse(status_code=400, content={"error": "Invalid messages payload."})
        messages = []
        for message in raw_messages:
            if not isinstance(message, dict):
                continue
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            role = str(message.get("role", "user")).strip().lower()
            messages.append(
                {
                    "role": role if role in {"user", "assistant", "model"} else "user",
                    "content": content[:100_000],
                }
            )
        agent_role = str(data.get("role", "default")).strip().lower() or "default"
        session_id = str(
            data.get("session_id", data.get("conversation_id", "default_session"))
        ).strip()[:200] or "default_session"
        requested_model = str(data.get("model", "")).strip()
        selected_model = (
            requested_model
            if requested_model in MODEL_REGISTRY
            else active_agent_models().get(agent_role, DEFAULT_AGENT_MODEL)
        )
        
        print(f"📡 [RECEIVE] Agent Role: [{agent_role}] | Session: {session_id}")
        
        if not GEMINI_KEYS_POOL:
            return JSONResponse(
                status_code=503,
                content={"error": "GEMINI_API_KEY is not configured."},
            )
        
        # Xoay tua API key: Chọn ngẫu nhiên 1 key trong danh sách để tránh Rate Limit
        selected_key = random.choice(GEMINI_KEYS_POOL)
        genai.configure(api_key=selected_key)
        print(f"🔄 [ROTATION] Using API Key ending in: ...{selected_key[-4:] if len(selected_key) > 4 else selected_key}")
        
        add_activity(agent_role, "đang xử lý", "Bắt đầu phân tích yêu cầu mới...")
        
        system_instruction = AGENT_PERSONAS.get(agent_role, AGENT_PERSONAS["default"])
        
        available_keys = [k for k in os.environ.keys() if k.endswith("_KEY") or k.endswith("_API_KEY")]
        key_list_str = ", ".join(available_keys) if available_keys else "Chưa có khóa nào"
        
        API_USAGE_INSTRUCTION = (
            f"\n\n[HƯỚNG DẪN QUAN TRỌNG VỀ CÁCH GIẢI QUYẾT YÊU CẦU BẰNG API]:\n"
            f"Các integration native đã được operator cấu hình cho các tên khóa sau: {key_list_str}. "
            f"Không đọc, in hoặc tiết lộ giá trị secret.\n"
            f"Nếu người dùng yêu cầu một chức năng cần dữ liệu bên ngoài, bạn PHẢI TỰ ĐỘNG THỰC HIỆN các bước sau:\n"
            f"1. Ưu tiên các tool native đã được khai báo (weather, news, stock, crypto, Wikipedia...).\n"
            f"2. Nếu chưa có tool phù hợp, dùng `search_public_apis_database` và ưu tiên API không cần auth.\n"
            f"3. `execute_python_code` là công cụ local nguy hiểm, bị tắt mặc định và không được truy cập secret. "
            f"Chỉ dùng nó khi operator đã bật và tác vụ thực sự cần thiết.\n"
            f"4. Chỉ yêu cầu người dùng cấu hình integration/key khi không có lựa chọn an toàn khác.\n"
            f"MỤC TIÊU CỦA BẠN LÀ HOÀN THÀNH NHIỆM VỤ THỰC TẾ thay vì chỉ giới thiệu API suông!"
        )
        
        WORKSPACE_USAGE_INSTRUCTION = (
            f"\n\n[QUY TẮC BẮT BUỘC VỀ LƯU TRỮ VÀ QUẢN LÝ TỆP TIN]:\n"
            f"Khi người dùng yêu cầu 'Tạo một dự án...', bạn tuyệt đối KHÔNG ĐƯỢC ném các tệp tin trực tiếp vào thư mục gốc.\n"
            f"Thay vào đó, TẤT CẢ các tệp tin, biểu đồ, source code của một dự án PHẢI được lưu bên trong thư mục 'projects/<tên_dự_án>/'.\n"
            f"Ví dụ: Nếu yêu cầu tạo Chatbot Pháp lý, bạn hãy ghi tệp vào các đường dẫn như: 'projects/legal-chatbot/main.py', 'projects/legal-chatbot/README.md'.\n"
            f"Hãy tự động áp dụng quy tắc này cho tất cả các công cụ (tool) có yêu cầu đường dẫn (path/filename)."
        )
        
        system_instruction += API_USAGE_INSTRUCTION + WORKSPACE_USAGE_INSTRUCTION
        
        # Chuẩn bị tin nhắn cho Gemini
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})
            
        if not gemini_messages:
            return {"choices": [{"message": {"content": "Không nhận diện được tin nhắn đầu vào."}}]}

        # Khởi tạo mô hình tích hợp kèm theo các public tools đã khai báo
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction,
            tools=PUBLIC_TOOLS
        )

        
        # Tạo phiên chat có bật cơ chế TỰ ĐỘNG GỌI HÀM (Automatic Function Calling)
        # Giúp Gemini tự động gọi các hàm Python (wttr.in, coingecko, wiki, ip-api) khi cần
        chat = model.start_chat(history=gemini_messages[:-1], enable_automatic_function_calling=True)
        
        last_message = gemini_messages[-1]["parts"][0]
        
        # Gửi tin nhắn và nhận phản hồi (SDK sẽ tự xử lý việc chạy hàm trung gian nếu Gemini yêu cầu)
        response = chat.send_message(last_message)
        
        # Ghi log lịch sử
        SESSION_MEMORY[session_id] = len(chat.history)
        STORE.replace_session_messages(
            session_id,
            agent_role,
            [*messages, {"role": "assistant", "content": response.text}],
        )
        print(f"✅ [RESPONSE] Trả lời thành công cho [{agent_role}]. Chiều dài lịch sử: {SESSION_MEMORY[session_id]}")
        add_activity(agent_role, "đã phản hồi", "Hoàn thành phân tích và trả lời người dùng.")
        
        # In ra các hàm đã được gọi trong lượt này (nêu có) để theo dõi
        for history_entry in chat.history[-2:]:
            for part in history_entry.parts:
                if part.function_call:
                    print(f"🛠️ [TOOL CALLED] Gemini đã kích hoạt Tool: {part.function_call.name} với tham số {part.function_call.args}")
                    add_activity(agent_role, "đã sử dụng công cụ", f"{part.function_call.name}")
        
        return {
            "choices": [
                {
                    "message": {
                        "content": response.text
                    }
                }
            ]
        }
    except Exception as e:
        import traceback
        print("❌ [ERROR] Lỗi xử lý Gemini:", traceback.format_exc())
        
        # --- OPENROUTER FALLBACK ---
        or_key = os.environ.get("OPENROUTER_API_KEY")
        if or_key:
            print("🔄 [FALLBACK] Đang chuyển hướng sang OpenRouter Free Models...")
            try:
                or_models = [
                    "google/gemma-4-31b-it:free",
                    "nvidia/nemotron-3-super-120b-a12b:free",
                    "tencent/hy3:free"
                ]
                selected_or_model = random.choice(or_models)
                print(f"🔄 [FALLBACK] Đã chọn model: {selected_or_model}")
                
                or_messages = [{"role": "system", "content": system_instruction}]
                for msg in messages:
                    or_role = msg.get("role", "user")
                    if or_role == "model": or_role = "assistant"
                    or_messages.append({"role": or_role, "content": msg.get("content", "")})
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {or_key}",
                        "HTTP-Referer": "http://localhost:5173",
                        "X-Title": "PerfectBlue Multi-Agent Dashboard",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": selected_or_model,
                        "messages": or_messages
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    fallback_text = data["choices"][0]["message"]["content"]
                    STORE.replace_session_messages(
                        session_id,
                        agent_role,
                        [*messages, {"role": "assistant", "content": fallback_text}],
                    )
                    add_activity(
                        agent_role,
                        "đã phản hồi",
                        f"Hoàn thành qua OpenRouter ({selected_or_model}).",
                    )
                    print(f"✅ [RESPONSE] Trả lời thành công qua OpenRouter [{agent_role}].")
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": fallback_text
                                }
                            }
                        ]
                    }
                else:
                    print("❌ [ERROR] Lỗi OpenRouter:", response.text)
            except Exception as or_e:
                print("❌ [ERROR] Lỗi kết nối OpenRouter:", or_e)
                
        add_activity(agent_role, "gặp lỗi", "Không thể hoàn thành yêu cầu.")
        return JSONResponse(
            status_code=500,
            content={"error": "Runtime failed to complete the request."},
        )

if __name__ == "__main__":
    import uvicorn
    runtime_host = os.environ.get("PERFECTBLUE_HOST", "127.0.0.1").strip()
    runtime_port = int(os.environ.get("PERFECTBLUE_PORT", "7770"))
    if runtime_host not in {"127.0.0.1", "localhost", "::1"} and not RUNTIME_TOKEN:
        raise RuntimeError(
            "PERFECTBLUE_RUNTIME_TOKEN is required when binding beyond localhost."
        )
    print("==================================================================")
    print("🌊   PERFECTBLUE CORE ENGINE - RUNNING ON PORT 7770")
    print("==================================================================")
    print("🎭 Loaded Roster (9 Agents):")
    for r in AGENT_PERSONAS.keys():
        if r != "default":
            print(f"  - [{r.upper()}]")
    print("🛠️  Loaded Tools (System & Public APIs Integration):")
    print("  - [get_weather]                 -> Hỗ trợ thời tiết (wttr.in)")
    print("  - [get_crypto_price]            -> Tra cứu coin (CoinGecko)")
    print("  - [search_wikipedia]            -> Tìm thông tin (Wikipedia API)")
    print("  - [get_my_location]             -> Xác định vị trí (ip-api)")
    print("  - [read_workspace_file]         -> Đọc tệp tin trong Workspace dự án")
    print("  - [write_workspace_file]        -> Ghi/tạo tệp tin mới trong Workspace")
    print("  - [execute_python_code]         -> Chạy Python local có kiểm soát (tắt mặc định)")
    print("  - [manage_project_tasks]        -> Quản lý công việc (list/create/update/delete)")
    print("  - [get_latest_hacker_news]      -> Tin tức công nghệ Hacker News")
    print("  - [get_github_repo_details]     -> Lấy thông tin Repo GitHub công khai")
    print("  - [search_public_apis_database] -> Tìm kiếm API trong kho 1400+ API cục bộ")
    print("  - [get_public_api_categories]   -> Xem danh sách danh mục API hiện có")
    print("==================================================================")

    uvicorn.run(app, host=runtime_host, port=runtime_port, log_level="warning")

