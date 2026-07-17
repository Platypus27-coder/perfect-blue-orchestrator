import os
import json
import random
import requests
import subprocess
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import google.generativeai as genai


app = FastAPI(title="PerfectBlue AI Runtime")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đọc cấu hình từ file .env cục bộ (tránh lộ Key lên GitHub)
env_path = ".env"
if not os.path.exists(env_path) and os.path.exists("../.env"):
    env_path = "../.env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                key, val = line.strip().split("=", 1)
                os.environ[key.strip()] = val.strip()

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
    html_content = f'''<!DOCTYPE html><html><head><title>{title}</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>body{{font-family:sans-serif;background:#1e1e1e;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}} .container{{width:80%;max-width:800px;background:#2d2d2d;padding:20px;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.5);}}</style></head><body><div class="container"><canvas id="myChart"></canvas></div><script>
    new Chart(document.getElementById('myChart'), {{
        type: '{chart_type}',
        data: {{
            labels: {labels_comma_separated.split(',')},
            datasets: [{{ label: '{title}', data: [{data_comma_separated}], backgroundColor: ['#ff6384','#36a2eb','#ffce56','#4bc0c0','#9966ff','#ff9f40'], borderColor: '#fff', borderWidth: 1 }}]
        }},
        options: {{ responsive: true }}
    }});
    </script></body></html>'''
    try:
        path = os.path.join(WORKSPACE_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return f"Đã tạo biểu đồ thành công tại {filename}. Hãy bảo người dùng mở file này trên trình duyệt để xem!"
    except Exception as e: return str(e)

def delegate_task_to_agent(target_agent: str, instructions: str) -> str:
    """Giao việc cho một Agent khác trong văn phòng và chờ nhận kết quả báo cáo.
    Dùng công cụ này khi bạn cần chuyên môn của bộ phận khác (Ví dụ: Programmer cần QA test, Manager cần Designer thiết kế).
    
    Args:
        target_agent: Tên agent nhận việc (programmer, qa, designer, manager, researcher, writer, support, devops, security).
        instructions: Lời nhắn/yêu cầu công việc chi tiết. Dặn dò rõ những gì cần làm.
    """
    import random
    
    system_inst = AGENT_PERSONAS.get(target_agent, AGENT_PERSONAS["default"])
    safe_tools = [t for t in PUBLIC_TOOLS if t.__name__ != "delegate_task_to_agent"]
    
    try:
        if GEMINI_KEYS_POOL:
            genai.configure(api_key=random.choice(GEMINI_KEYS_POOL))
        model = genai.GenerativeModel(
            model_name='gemini-3.5-flash',
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
    import random
    
    # Bỏ chính tool này và tool delegate cũ ra khỏi danh sách để tránh đẻ đệ quy vô hạn
    safe_tools = [t for t in PUBLIC_TOOLS if t.__name__ not in ["delegate_task_to_agent", "recruit_expert_and_delegate_task"]]
    
    try:
        if GEMINI_KEYS_POOL:
            genai.configure(api_key=random.choice(GEMINI_KEYS_POOL))
        model = genai.GenerativeModel(
            model_name='gemini-3.5-flash',
            system_instruction=expert_system_prompt,
            tools=safe_tools
        )
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(instructions)
        return f"[BÁO CÁO TỪ CHUYÊN GIA MỚI TUYỂN DỤNG - {expert_title.upper()}]:\n{response.text}"
    except Exception as e:
        return f"Lỗi khi tuyển dụng và giao việc cho {expert_title}: {str(e)}"

# --- Cấu hình Thư mục Workspace An toàn ---
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_workspace_file(relative_path: str) -> str:
    """Đọc nội dung của một tệp tin trong thư mục dự án (workspace).
    
    Args:
        relative_path: Đường dẫn tương đối từ gốc dự án (Ví dụ: 'README.md' hoặc 'backend/main.py').
    """
    try:
        safe_path = os.path.abspath(os.path.join(WORKSPACE_DIR, relative_path))
        if not safe_path.startswith(WORKSPACE_DIR):
            return "Lỗi: Không được phép truy cập tệp ngoài thư mục dự án."
        if not os.path.exists(safe_path):
            return f"Lỗi: Tệp '{relative_path}' không tồn tại."
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Lỗi đọc tệp: {str(e)}"

def write_workspace_file(relative_path: str, content: str) -> str:
    """Ghi hoặc cập nhật nội dung của một tệp tin trong thư mục dự án (workspace).
    
    Args:
        relative_path: Đường dẫn tương đối từ gốc dự án (Ví dụ: 'docs/architecture.md' hoặc 'backend/test_script.py').
        content: Nội dung văn bản cần ghi vào tệp.
    """
    try:
        safe_path = os.path.abspath(os.path.join(WORKSPACE_DIR, relative_path))
        if not safe_path.startswith(WORKSPACE_DIR):
            return "Lỗi: Không được phép ghi tệp ngoài thư mục dự án."
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Thành công: Đã tạo/ghi nội dung vào tệp '{relative_path}'."
    except Exception as e:
        return f"Lỗi ghi tệp: {str(e)}"

def execute_python_code(code: str) -> str:
    """Chạy một đoạn mã Python (sandbox) và trả về kết quả Console đầu ra (stdout/stderr).
    Hữu dụng cho lập trình viên chạy thử thuật toán hoặc test code.
    
    Args:
        code: Đoạn code Python hoàn chỉnh cần thực thi.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = ""
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr}\n"
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
    tasks_file = os.path.join(WORKSPACE_DIR, "tasks.json")
    tasks = []
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except:
            tasks = []
            
    if action == "list":
        if not tasks:
            return "Danh sách công việc đang trống. Hãy tạo công việc đầu tiên!"
        res = "Danh sách công việc dự án:\n"
        for t in tasks:
            res += f"- ID [{t.get('id')}] | Trạng thái: [{t.get('status').upper()}] | Tiêu đề: {t.get('title')} ({t.get('description')})\n"
        return res
        
    elif action == "create":
        new_id = max([t["id"] for t in tasks]) + 1 if tasks else 1
        new_task = {
            "id": new_id,
            "title": title,
            "description": description,
            "status": status
        }
        tasks.append(new_task)
        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
        return f"Thành công: Đã tạo công việc ID {new_id} - '{title}'."
        
    elif action == "update":
        if not task_id:
            return "Lỗi: Thiếu tham số task_id để cập nhật."
        for t in tasks:
            if t["id"] == task_id:
                if title: t["title"] = title
                if description: t["description"] = description
                if status: t["status"] = status
                with open(tasks_file, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=2, ensure_ascii=False)
                return f"Thành công: Đã cập nhật công việc ID {task_id}."
        return f"Lỗi: Không tìm thấy công việc ID {task_id}."
        
    elif action == "delete":
        if not task_id:
            return "Lỗi: Thiếu tham số task_id để xóa."
        initial_len = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]
        if len(tasks) < initial_len:
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
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
GLOBAL_ACTIVITIES = []

def add_activity(agent_name: str, action: str, detail: str):
    import datetime
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    act = {
        "agent": agent_name.capitalize(),
        "action": action,
        "detail": detail,
        "time": now_str
    }
    GLOBAL_ACTIVITIES.append(act)
    if len(GLOBAL_ACTIVITIES) > 20:
        GLOBAL_ACTIVITIES.pop(0)

@app.get("/api/v1/activities")
def get_activities():
    # Trả về đảo ngược để mới nhất lên đầu
    return {"activities": GLOBAL_ACTIVITIES[::-1]}

@app.get("/health")
def health():
    return {"ok": True, "status": "healthy - PerfectBlue Core Engine is active with Tools"}

ACTIVE_AGENTS = {
    "programmer": "gemini-3.5-flash",
    "qa": "gemini-3.5-flash",
    "designer": "gemini-3.5-flash",
    "manager": "gemini-3.5-flash",
    "researcher": "gemini-3.5-flash",
    "writer": "gemini-3.5-flash",
    "support": "gemini-3.5-flash",
    "devops": "gemini-3.5-flash",
    "security": "gemini-3.5-flash"
}

@app.get("/state")
def state():
    # Khai báo ĐẦY ĐỦ các agent cùng với model tương ứng cho Claw3D nhận diện
    return {
        "identity": {
            "name": "PerfectBlue Master Brain",
            "role": "orchestrator"
        },
        "runtime": {
            "name": "PerfectBlue Core",
            "active_model": "gemini-3.5-flash",
            "status": "Running"
        },
        "active": ACTIVE_AGENTS
    }

@app.post("/agents/add")
async def add_agent_endpoint(request: Request):
    data = await request.json()
    role_id = data.get("id", data.get("role", "custom")).lower()
    model = data.get("model", "gemini-3.5-flash")
    ACTIVE_AGENTS[role_id] = model
    
    if role_id not in AGENT_PERSONAS:
        desc = data.get("description", f"Bạn là một {role_id} chuyên nghiệp.")
        AGENT_PERSONAS[role_id] = desc

    return {"ok": True, "agent": {"id": role_id, "model": model}}

@app.get("/registry")
def registry():
    return {
        "models": {
            "gemini-3.5-flash": {"speed": "fast", "cost": "free", "features": ["tools", "system_instructions"]},
            "gemini-3.1-pro": {"speed": "moderate", "cost": "free", "features": ["tools", "system_instructions"]}
        }
    }


# --- Giai đoạn 1 & 4: LLM Engine & Định tuyến lệnh (Routing) & Thực thi Tools ---
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    agent_role = data.get("role", "default")
    session_id = data.get("session_id", "default_session")
    
    print(f"📡 [RECEIVE] Agent Role: [{agent_role}] | Session: {session_id}")
    
    if not GEMINI_KEYS_POOL:
        return {"choices": [{"message": {"content": f"[{agent_role.upper()}] Chào bạn! Tôi chưa được cấu hình khóa GEMINI_API_KEY trong file .env nên chưa thể suy nghĩ thực tế được. Xin hãy điền key vào nhé!"}}]}
    
    # Xoay tua API key: Chọn ngẫu nhiên 1 key trong danh sách để tránh Rate Limit
    selected_key = random.choice(GEMINI_KEYS_POOL)
    genai.configure(api_key=selected_key)
    print(f"🔄 [ROTATION] Using API Key ending in: ...{selected_key[-4:] if len(selected_key) > 4 else selected_key}")
    
    agent_role = data.get("role", "default")
    
    add_activity(agent_role, "đang xử lý", "Bắt đầu phân tích yêu cầu mới...")
    
    system_instruction = AGENT_PERSONAS.get(agent_role, AGENT_PERSONAS["default"])
    
    available_keys = [k for k in os.environ.keys() if k.endswith("_KEY") or k.endswith("_API_KEY")]
    key_list_str = ", ".join(available_keys) if available_keys else "Chưa có khóa nào"
    
    API_USAGE_INSTRUCTION = (
        f"\n\n[HƯỚNG DẪN QUAN TRỌNG VỀ CÁCH GIẢI QUYẾT YÊU CẦU BẰNG API]:\n"
        f"LƯU Ý: Bạn ĐÃ CÓ SẴN các khóa API sau trong môi trường (dùng `os.environ.get('TÊN_KHÓA')` để lấy): {key_list_str}\n"
        f"Nếu người dùng yêu cầu một chức năng cần dữ liệu bên ngoài, bạn PHẢI TỰ ĐỘNG THỰC HIỆN các bước sau:\n"
        f"1. Dùng tool `search_public_apis_database` để tìm API phù hợp.\n"
        f"2. LUÔN LUÔN ƯU TIÊN SỬ DỤNG các API có cột `auth` là 'No' (không cần key) để tiết kiệm thời gian.\n"
        f"3. Nếu tìm thấy API 'No Auth', hoặc API yêu cầu khóa nhưng khóa đó đã CÓ SẴN trong danh sách trên, bạn hãy NGAY LẬP TỨC tự viết script gọi API đó bằng tool `execute_python_code` (dùng `requests`), đọc kết quả và trả lời.\n"
        f"4. Chỉ khi API yêu cầu khóa (auth != 'No') và khóa đó CHƯA CÓ trong danh sách trên, bạn mới DỪNG LẠI và yêu cầu người dùng cung cấp key (ví dụ: 'Để lấy dữ liệu này, tôi cần API Key của dịch vụ X').\n"
        f"MỤC TIÊU CỦA BẠN LÀ HOÀN THÀNH NHIỆM VỤ THỰC TẾ thay vì chỉ giới thiệu API suông!"
    )
    system_instruction += API_USAGE_INSTRUCTION
    
    # Chuẩn bị tin nhắn cho Gemini
    gemini_messages = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        gemini_messages.append({"role": role, "parts": [msg["content"]]})
        
    if not gemini_messages:
        return {"choices": [{"message": {"content": "Không nhận diện được tin nhắn đầu vào."}}]}

    try:
        # Khởi tạo mô hình tích hợp kèm theo các public tools đã khai báo
        model = genai.GenerativeModel(
            model_name='gemini-3.5-flash',
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
        print("❌ [ERROR] Lỗi xử lý Gemini:", e)
        
        # --- OPENROUTER FALLBACK ---
        or_key = os.environ.get("OPENROUTER_API_KEY")
        if or_key:
            print("🔄 [FALLBACK] Đang chuyển hướng sang OpenRouter Free Models...")
            try:
                import requests
                import random
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
                
        return {"choices": [{"message": {"content": f"Lỗi hệ thống: {str(e)}"}}] }

if __name__ == "__main__":
    import uvicorn
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
    print("  - [execute_python_code]         -> Thực thi mã lệnh Python (Sandbox)")
    print("  - [manage_project_tasks]        -> Quản lý công việc (list/create/update/delete)")
    print("  - [get_latest_hacker_news]      -> Tin tức công nghệ Hacker News")
    print("  - [get_github_repo_details]     -> Lấy thông tin Repo GitHub công khai")
    print("  - [search_public_apis_database] -> Tìm kiếm API trong kho 1400+ API cục bộ")
    print("  - [get_public_api_categories]   -> Xem danh sách danh mục API hiện có")
    print("==================================================================")

    uvicorn.run(app, host="0.0.0.0", port=7770, log_level="warning")

