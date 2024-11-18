from flask import Flask, render_template, request, jsonify
import pandas as pd
from fuzzywuzzy import fuzz, process
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
import re

app = Flask(__name__)

# Bảng ánh xạ mã ngôn ngữ sang tên đầy đủ
LANGUAGE_MAP = {
    "vi": "Vietnamese",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "ja": "Japanese",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "de": "German",
    "ru": "Russian",
    "ar": "Arabic",
    "ko": "Korean",
    "it": "Italian",
    "pt": "Portuguese",
    "hi": "Hindi",
    "th": "Thai",
    "unknown": "Unknown"
}

CSV_PATH = "Language Detection.csv"

# Tải dữ liệu từ CSV
def load_data():
    try:
        return pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        # Nếu file không tồn tại, tạo một file mới
        df = pd.DataFrame(columns=["Text", "Language"])
        df.to_csv(CSV_PATH, index=False)
        return df

def save_feedback(text, language):
    # Tải dữ liệu từ file CSV
    data = load_data()

    # Tạo DataFrame mới với dữ liệu phản hồi
    new_entry = pd.DataFrame([{"Text": text.strip(), "Language": language.strip()}])

    # Kết hợp dữ liệu cũ với dòng mới
    data = pd.concat([data, new_entry], ignore_index=True)

    # Ghi lại file CSV
    try:
        data.to_csv(CSV_PATH, index=False)
    except Exception as e:
        print(f"Lỗi khi lưu phản hồi: {e}")
        raise e

@app.route("/")
def index():
    return render_template("index.html")

def is_gibberish(text):
    # Nếu văn bản rỗng, coi là vô nghĩa
    if not text.strip():
        return True

    # Nếu văn bản chỉ có ký tự đặc biệt hoặc số
    if not any(c.isalpha() for c in text):
        return True

    # Nếu văn bản có ít hơn 3 ký tự, không đủ để xác định ngôn ngữ
    if len(text) < 3:
        return False  # Cho phép langdetect xử lý

    # Nếu văn bản quá dài mà không có khoảng trắng (không có từ hợp lệ)
    if len(text) >= 10 and " " not in text:
        return True

    # Nếu văn bản chứa dấu tiếng Việt hoặc có từ hợp lệ, không coi là vô nghĩa
    if re.search(r'[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', text) or re.search(r'\b\w+\b', text):
        return False

    return False



@app.route("/detect", methods=["POST"])
def detect_language():
    data = load_data()
    text = request.json.get("text", "").strip()

    if is_gibberish(text):
        return jsonify({"language": "Unknown", "source": "validation"})

    choices = data["Text"].tolist()
    best_match, score = process.extractOne(text, choices, scorer=fuzz.ratio)

    if score > 80:  
        matched_row = data[data["Text"] == best_match]
        language_code = matched_row["Language"].values[0]
        language_name = LANGUAGE_MAP.get(language_code, "Unknown")
        return jsonify({"language": language_name, "source": "csv", "match_score": score})

    # Nếu không tìm thấy trong CSV, chuyển sang langdetect
    try:
        detected_language = detect(text)
        language_name = LANGUAGE_MAP.get(detected_language, "Unknown")
        return jsonify({"language": language_name, "source": "langdetect"})
    except LangDetectException:
        return jsonify({"language": "Unknown", "source": "langdetect"})

    # Fallback: Phát hiện ngôn ngữ bằng langdetect
    try:
        detected_language = detect(text)
        language_name = LANGUAGE_MAP.get(detected_language, "Unknown")
    except LangDetectException:
        language_name = "Unknown"

    return jsonify({"language": language_name, "source": "langdetect"})

    try:
        detected_language = detect(text)
        language_name = LANGUAGE_MAP.get(detected_language, "Unknown")
    except LangDetectException:
        language_name = "Unknown"

    return jsonify({"language": language_name, "source": "langdetect"})

@app.route("/feedback", methods=["POST"])
def feedback():
    # Nhận dữ liệu từ người dùng
    text = request.json.get("text", "").strip()
    language = request.json.get("language", "").strip()

    # Kiểm tra dữ liệu đầu vào
    if not text or not language:
        return jsonify({"message": "Error: Text or language is missing"}), 400

    # Thêm dữ liệu vào file CSV
    try:
        save_feedback(text, language)
        return jsonify({"message": "Feedback saved successfully!"})
    except Exception as e:
        return jsonify({"message": f"Error saving feedback: {e}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
