import os
import json
import requests
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

# Khởi tạo Gemini
if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

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

# Danh sách các tool công khai tích hợp cho Gemini
PUBLIC_TOOLS = [get_weather, get_crypto_price, search_wikipedia, get_my_location]

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

@app.get("/health")
def health():
    return {"ok": True, "status": "healthy - PerfectBlue Core Engine is active with Tools"}

@app.get("/state")
def state():
    # Khai báo ĐẦY ĐỦ 9 agent cùng với model tương ứng cho Claw3D nhận diện
    return {
        "identity": {
            "name": "PerfectBlue Master Brain",
            "role": "orchestrator"
        },
        "runtime": {
            "name": "PerfectBlue Core",
            "active_model": "gemini-1.5-flash",
            "status": "Running"
        },
        "active": {
            "programmer": "gemini-1.5-flash",
            "qa": "gemini-1.5-flash",
            "designer": "gemini-1.5-flash",
            "manager": "gemini-1.5-flash",
            "researcher": "gemini-1.5-flash",
            "writer": "gemini-1.5-flash",
            "support": "gemini-1.5-flash",
            "devops": "gemini-1.5-flash",
            "security": "gemini-1.5-flash"
        }
    }

@app.get("/registry")
def registry():
    return {
        "models": {
            "gemini-1.5-flash": {"speed": "fast", "cost": "free", "features": ["tools", "system_instructions"]},
            "gemini-1.5-pro": {"speed": "moderate", "cost": "free", "features": ["tools", "system_instructions"]}
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
    
    if not os.environ.get("GEMINI_API_KEY"):
        return {"choices": [{"message": {"content": f"[{agent_role.upper()}] Chào bạn! Tôi chưa được cấu hình khóa GEMINI_API_KEY trong file main.py hoặc biến môi trường nên chưa thể suy nghĩ thực tế được. Xin hãy điền key vào nhé!"}}]}
    
    system_instruction = AGENT_PERSONAS.get(agent_role, AGENT_PERSONAS["default"])
    
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
            model_name='gemini-1.5-flash',
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
        
        # In ra các hàm đã được gọi trong lượt này (nêu có) để theo dõi
        for history_entry in chat.history[-2:]:
            for part in history_entry.parts:
                if part.function_call:
                    print(f"🛠️ [TOOL CALLED] Gemini đã kích hoạt Tool: {part.function_call.name} với tham số {part.function_call.args}")
        
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
        print("❌ [ERROR] Lỗi xử lý:", e)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    print("==================================================================")
    print("🌊   PERFECTBLUE CORE ENGINE - RUNNING ON PORT 7770")
    print("==================================================================")
    print("🎭 Loaded Roster (9 Agents):")
    for r in AGENT_PERSONAS.keys():
        if r != "default":
            print(f"  - [{r.upper()}]")
    print("🛠️  Loaded Tools (Public APIs Integration):")
    print("  - [get_weather]       -> Hỗ trợ thời tiết (wttr.in)")
    print("  - [get_crypto_price]  -> Tra cứu coin (CoinGecko)")
    print("  - [search_wikipedia]  -> Tìm thông tin (Wikipedia API)")
    print("  - [get_my_location]   -> Xác định vị trí (ip-api)")
    print("==================================================================")
    uvicorn.run(app, host="0.0.0.0", port=7770, log_level="warning")
