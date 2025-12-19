"""
Response Configuration - Centralized Messages

Tất cả các câu trả lời của bot tập trung tại đây để dễ customize.

Design Pattern: Configuration as Code
- Single source of truth cho UI/UX
- Easy A/B testing
- Multilingual support ready

Enhanced with Dual-Output Support:
- display_message: Rich formatting for UI
- tts_message: Clean text for voice reading
- Modes: TEMPLATE (fast) or LLM (natural)
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum
import re

from agent.utils.logging import get_logger

logger = get_logger(__name__)

class ResponseMode(Enum):
    """Response generation mode."""
    TEMPLATE = "template"  # Fast, template-based
    LLM = "llm"           # Natural, LLM-enhanced


@dataclass
class ResponseTemplate:
    """Enhanced template với dual-output support."""
    key: str
    description: str
    variables: List[str]
    
    # Display output (for UI - can have markdown, emojis)
    display_template: str
    display_mode: ResponseMode = ResponseMode.TEMPLATE
    display_llm_prompt: Optional[str] = None
    
    # Text message output (for voice reading - clean text)
    tts_message_template: Optional[str] = None  # None = auto-clean from display
    tts_message_mode: ResponseMode = ResponseMode.TEMPLATE
    tts_message_llm_prompt: Optional[str] = None
    
    # Metadata
    priority: str = "normal"  # high/normal/low - affects processing priority
    
    # Legacy support
    @property
    def template(self) -> str:
        """Backward compatibility."""
        return self.display_template
    
    def format(self, **kwargs) -> str:
        """Backward compatibility - format display template."""
        return self.format_display(**kwargs)
    
    def format_display(self, **kwargs) -> str:
        """Format display template (template mode only)."""
        if self.display_mode != ResponseMode.TEMPLATE:
            raise ValueError(f"Cannot format - display_mode is {self.display_mode.value}")
        return self.display_template.format(**kwargs)
    
    def format_tts_message(self, **kwargs) -> str:
        """Format tts_message template (template mode only)."""
        if self.tts_message_mode != ResponseMode.TEMPLATE:
            raise ValueError(f"Cannot format - tts_message_mode is {self.tts_message_mode.value}")
        
        if self.tts_message_template:
            return self.tts_message_template.format(**kwargs)
        
        # Fallback: clean from display
        if self.display_mode == ResponseMode.TEMPLATE:
            display = self.display_template.format(**kwargs)
            return clean_markdown(display)
        
        raise ValueError("Cannot auto-generate tts_message from LLM display")
    
    def needs_llm(self) -> bool:
        """Check if any output needs LLM generation."""
        return (self.display_mode == ResponseMode.LLM or 
                self.tts_message_mode == ResponseMode.LLM)


# ==================== BASIC INFO COLLECTION ====================

ASK_BASIC_MISSING = ResponseTemplate(
    key="ask_basic_missing",
    description="Hỏi thông tin cơ bản còn thiếu",
    variables=["missing_fields"],

    # -------- DISPLAY (UI) --------
    # Tự động format danh sách fields theo dạng bullet.
    display_template=(
        "Để tiếp tục đặt lịch, bạn vui lòng bổ sung các thông tin sau:\n"
        "{missing_fields}"
    ),
    display_mode=ResponseMode.TEMPLATE,
    display_llm_prompt=(
        "Bạn là trợ lý hỗ trợ đặt lịch. Hãy tạo nội dung hiển thị trên UI để "
        "hỏi người dùng cung cấp các thông tin còn thiếu. Nội dung cần:\n"
        "- Ngắn gọn, lịch sự, đúng trọng tâm.\n"
        "- Giữ nguyên câu mở đầu: 'Để tiếp tục đặt lịch, bạn vui lòng bổ sung các thông tin sau:'\n"
        "- Danh sách {missing_fields} đã được xử lý sẵn thành dạng bullet (không sinh lại).\n"
        "- Không thêm mô tả thừa, không hỏi lại theo cách khác.\n"
        "Hãy trả về đúng một đoạn text hoàn chỉnh, không markdown đặc biệt ngoài bullet."
    ),

    # -------- TTS (VOICE) --------
    # Giọng đọc tự nhiên, tránh đọc bullet, tránh đọc ký tự thừa.
    # Tự động chuyển list thành chuỗi đọc tự nhiên trong processing layer.
    tts_message_template=(
        "Để tiếp tục đặt lịch, tôi cần bạn cung cấp thêm các thông tin sau: "
        "{missing_fields}. "
        "Bạn có thể trả lời trực tiếp từng thông tin nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    priority="high"
)


ASK_BASIC_ERROR = ResponseTemplate(
    key="ask_basic_error",
    description="Báo lỗi validation và yêu cầu người dùng nhập lại thông tin",
    variables=["error_message", "missing_fields"],

    # -------- DISPLAY (UI) --------
    # Hiển thị error rõ ràng, sau đó hỏi lại bằng bullet list
    display_template=(
        "{error_message}\n\n"
        "Vui lòng cung cấp lại các thông tin sau:\n"
        "{missing_fields}"
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    # TTS tránh xuống dòng, tránh bullet, đọc mượt và tự nhiên.
    tts_message_template=(
        "{error_message}. "
        "Bạn vui lòng cung cấp lại các thông tin sau: {missing_fields}. "
        "Bạn có thể trả lời trực tiếp nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    priority="high"
)


# ==================== PREFERENCE SELECTION ====================

ASK_PREFERENCE = ResponseTemplate(
    key="ask_preference",
    description="Hỏi người dùng chọn kiểu đặt lịch nhanh hoặc chi tiết",
    variables=[],

    # -------- DISPLAY (UI) --------
    display_template=(
        "Tôi đã có đầy đủ thông tin cơ bản.\n"
        "Bạn muốn tiếp tục theo cách nào?\n\n"
        "- **Đặt nhanh**: Nhân viên sẽ gọi lại để hỗ trợ.\n"
        "- **Đặt chi tiết**: Bạn tự chọn ngày, giờ và chuyên khoa."
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Tôi đã có đầy đủ thông tin cơ bản. "
        "Bạn muốn đặt nhanh để nhân viên gọi lại hỗ trợ, "
        "hay đặt chi tiết để tự chọn ngày, giờ và chuyên khoa?"
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


# ==================== DETAILED BOOKING - HOSPITAL ====================

ASK_DETAILED_HOSPITAL_BIRTH_SEX = ResponseTemplate(
    key="ask_detailed_hospital_birth_sex",
    description="Hỏi ngày sinh và giới tính khi đặt lịch tại bệnh viện",
    variables=[],

    # -------- DISPLAY (UI) --------
    display_template=(
        "Để hoàn tất đặt lịch khám tại bệnh viện, vui lòng cung cấp thêm:\n"
        "- Ngày sinh (định dạng: dd-mm-yyyy)\n"
        "- Giới tính (Nam/Nữ)"
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Để hoàn tất đặt lịch khám tại bệnh viện, "
        "bạn vui lòng cho tôi biết ngày sinh theo định dạng ngày tháng năm, "
        "và giới tính là Nam hay Nữ."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


ASK_DETAILED_HOSPITAL_FACILITY = ResponseTemplate(
    key="ask_detailed_hospital_facility",
    description="Hỏi người dùng chọn cơ sở khám sau khi đã hiển thị danh sách",
    variables=[],

    # -------- DISPLAY (UI) --------
    display_template=(
        "Bạn muốn khám tại cơ sở nào?\n"
        "Vui lòng cung cấp **tên cơ sở** hoặc **số thứ tự** trong danh sách."
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Bạn muốn khám tại cơ sở nào? "
        "Bạn có thể nói tên cơ sở, hoặc đọc số thứ tự trong danh sách."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


ASK_DETAILED_HOSPITAL_DATETIME = ResponseTemplate(
    key="ask_detailed_hospital_datetime",
    description="Hỏi người dùng chọn ngày và giờ khám",
    variables=[],

    # -------- DISPLAY (UI) --------
    display_template=(
        "Bạn muốn đặt lịch vào **ngày** và **giờ** nào?\n"
        "Giờ làm việc của bệnh viện: **07:30 – 17:00**."
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Bạn muốn đặt lịch vào ngày và giờ nào? "
        "Giờ làm việc của bệnh viện là từ bảy giờ ba mươi sáng đến năm giờ chiều."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


ASK_DETAILED_HOSPITAL_REASON_SPECIALIST = ResponseTemplate(
    key="ask_detailed_hospital_reason_specialist",
    description="Hỏi chuyên khoa và lý do khám (deprecated – dùng phiên bản mới nếu có)",
    variables=[],

    # -------- DISPLAY (UI) --------
    display_template=(
        "Bạn muốn khám **chuyên khoa** nào? \n"
        "Vui lòng cho tôi biết thêm **lý do khám** để hỗ trợ bạn chính xác hơn."
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Bạn muốn khám chuyên khoa nào? "
        "Bạn cũng vui lòng cho tôi biết lý do khám để tôi hỗ trợ chính xác hơn."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


ASK_DETAILED_HOSPITAL_REASON_WITH_SPECIALISTS = ResponseTemplate(
    key="ask_detailed_hospital_reason_with_specialists",
    description="Hỏi lý do khám và chuyên khoa khi đã có danh sách chuyên khoa gợi ý",
    variables=["specialist_list"],

    # -------- DISPLAY (UI) --------
    display_template=(
        "**Bạn muốn khám chuyên khoa nào và lý do khám là gì?**\n\n"
        "💡 _Nếu bạn chưa muốn cung cấp ngay, có thể bỏ qua bước này._\n\n"
        "{specialist_list}"
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Bạn muốn khám chuyên khoa nào và lý do khám là gì? "
        "Nếu bạn chưa muốn cung cấp ngay, bạn có thể bỏ qua bước này. "
        "{specialist_list}"
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


ASK_DETAILED_HOSPITAL_REASON_NO_SPECIALISTS = ResponseTemplate(
    key="ask_detailed_hospital_reason_no_specialists",
    description="Hỏi lý do khám khi chưa có danh sách chuyên khoa (fallback)",
    variables=[],

    # -------- DISPLAY (UI) --------
    display_template=(
        "**Lý do khám** của bạn là gì?\n"
        "_Ví dụ: Khám sức khỏe định kỳ, đau đầu, mệt mỏi kéo dài._\n\n"
        "💡 _Bạn cũng có thể cho biết **chuyên khoa** nếu muốn._"
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Lý do khám của bạn là gì? "
        "Ví dụ như khám sức khỏe định kỳ, đau đầu, hoặc mệt mỏi kéo dài. "
        "Bạn cũng có thể cho biết chuyên khoa nếu muốn."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


# ==================== DETAILED BOOKING - HOME ====================

ASK_DETAILED_HOME_BIRTH_SEX = ResponseTemplate(
    key="ask_detailed_home_birth_sex",
    description="Hỏi ngày sinh và giới tính khi đặt lịch khám tại nhà",
    variables=[],

    # -------- DISPLAY (UI) --------
    display_template=(
        "Để hoàn tất đặt lịch khám tại nhà, vui lòng cung cấp thêm:\n"
        "- Ngày sinh (định dạng: dd-mm-yyyy)\n"
        "- Giới tính (Nam/Nữ)"
    ),
    display_mode=ResponseMode.TEMPLATE,

    # -------- TTS (VOICE) --------
    tts_message_template=(
        "Để hoàn tất đặt lịch khám tại nhà, "
        "bạn vui lòng cho tôi biết ngày sinh theo định dạng ngày tháng năm, "
        "và giới tính là Nam hay Nữ."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


ASK_DETAILED_HOME_ADDRESS = ResponseTemplate(
    key="ask_detailed_home_address",
    display_template=(
        "Địa chỉ nhà bạn là gì?\n"
        "Vui lòng cung cấp **phường/xã** và **địa chỉ cụ thể**."
    ),
    tts_message_template=(
        "Địa chỉ nhà bạn là gì? "
        "Vui lòng cung cấp phường hoặc xã và địa chỉ cụ thể."
    ),
    description="Hỏi địa chỉ đầy đủ cho dịch vụ khám tại nhà",
    variables=[]
)


ASK_DETAILED_HOME_DATETIME = ResponseTemplate(
    key="ask_detailed_home_datetime",
    display_template=(
        "Bạn muốn đặt lịch vào **ngày** và **giờ** nào?\n"
        "⏰ Giờ làm việc: 7:30 – 17:00."
    ),
    tts_message_template=(
        "Bạn muốn đặt lịch vào ngày và giờ nào? "
        "Giờ làm việc từ 7 giờ 30 sáng đến 5 giờ chiều."
    ),
    description="Hỏi ngày và giờ hẹn cho dịch vụ khám tại nhà",
    variables=[]
)


ASK_DETAILED_HOME_REASON = ResponseTemplate(
    key="ask_detailed_home_reason",
    display_template=(
        "Lý do bạn muốn **khám bệnh tại nhà** là gì?\n"
        "💡 Ví dụ: Đau đầu, sốt, kiểm tra sức khỏe, khó di chuyển..."
    ),
    tts_message_template=(
        "Lý do bạn muốn khám bệnh tại nhà là gì? "
        "Ví dụ như đau đầu, sốt, kiểm tra sức khỏe hoặc khó di chuyển."
    ),
    description="Hỏi lý do khám tại nhà (bắt buộc)",
    variables=[]
)


# ==================== DETAILED BOOKING - TEST AT HOME ====================

ASK_DETAILED_TEST_BIRTH_SEX = ResponseTemplate(
    key="ask_detailed_test_birth_sex",
    display_template=(
        "Để đặt lịch **xét nghiệm tại nhà**, tôi cần thêm:\n"
        "- Ngày sinh (dd-mm-yyyy)\n"
        "- Giới tính (Nam/Nữ)"
    ),
    tts_message_template=(
        "Để đặt lịch xét nghiệm tại nhà, tôi cần thêm ngày sinh theo định dạng "
        "ngày tháng năm và giới tính Nam hoặc Nữ."
    ),
    description="Hỏi ngày sinh và giới tính cho dịch vụ xét nghiệm tại nhà",
    variables=[]
)


ASK_DETAILED_TEST_ADDRESS = ResponseTemplate(
    key="ask_detailed_test_address",
    display_template=(
        "Địa chỉ bạn muốn lấy mẫu xét nghiệm tại nhà ở đâu?\n"
        "(Vui lòng cung cấp Phường/Xã và địa chỉ cụ thể)"
    ),
    tts_message_template=(
        "Địa chỉ bạn muốn lấy mẫu xét nghiệm tại nhà ở đâu? "
        "Vui lòng cung cấp phường hoặc xã và địa chỉ cụ thể."
    ),
    description="Hỏi địa chỉ đầy đủ cho dịch vụ xét nghiệm tại nhà",
    variables=[]
)


ASK_DETAILED_TEST_DATETIME = ResponseTemplate(
    key="ask_detailed_test_datetime",
    display_template=(
        "Bạn muốn đặt lịch **xét nghiệm tại nhà** vào ngày và giờ nào?\n"
        "(Giờ làm việc: 6:00–22:00)"
    ),
    tts_message_template=(
        "Bạn muốn đặt lịch xét nghiệm tại nhà vào ngày và giờ nào? "
        "Giờ làm việc từ sáu giờ sáng đến mười giờ tối."
    ),
    description="Hỏi ngày giờ hẹn cho dịch vụ xét nghiệm tại nhà (khung giờ rộng)",
    variables=[]
)


# ==================== CONFIRMATION ====================

CONFIRM_BOOKING_QUICK = ResponseTemplate(
    key="confirm_booking_quick",
    display_template=(
        "📋 **Xác nhận thông tin đặt lịch nhanh**\n\n"
        "👤 **Người đặt:** {name}\n"
        "📞 **Số điện thoại:** {phone}\n"
        "🏥 **Hình thức:** {method_type}\n\n"
        "✨ Nhân viên Medlatec sẽ liên hệ với bạn để xác nhận chi tiết.\n\n"
        "**Thông tin trên đã chính xác chưa?**"
    ),
    display_mode=ResponseMode.LLM,
    display_llm_prompt=(
        "Rewrite the message to be warm, supportive, and professionally friendly. "
        "Keep all data fields exactly as they are, preserving structure and emojis. "
        "Make the assistant sound like a caring medical support staff who is calmly "
        "double-checking the information before proceeding."
    ),
    tts_message_template=(
        "Tôi xin xác nhận lại thông tin đặt lịch nhanh. "
        "Người đặt là {name}, số điện thoại {phone}, và hình thức là {method_type}. "
        "Nhân viên Medlatec sẽ liên hệ để xác nhận chi tiết. "
        "Thông tin này đã chính xác chưa?"
    ),
    description="Xác nhận thông tin quick booking",
    variables=["name", "phone", "method_type"]
)


CONFIRM_BOOKING_HOSPITAL = ResponseTemplate(
    key="confirm_booking_hospital",
    description="Xác nhận thông tin hospital booking",
    variables=[
        "name", "phone", "birth_date", "sex",
        "facility_name", "appointment_date",
        "appointment_time", "optional_info"
    ],

    # Display: LLM rewrite để tạo giọng ấm áp, chuyên nghiệp
    display_template=(
        "📋 **Xác nhận thông tin đặt lịch khám tại viện**\n\n"
        "👤 **Họ tên:** {name}\n"
        "📞 **Số điện thoại:** {phone}\n"
        "🎂 **Ngày sinh:** {birth_date}\n"
        "⚧ **Giới tính:** {sex}\n"
        "🏥 **Cơ sở khám:** {facility_name}\n"
        "📅 **Ngày hẹn:** {appointment_date}\n"
        "🕐 **Giờ hẹn:** {appointment_time}\n"
        "{optional_info}"
        "\n\n**Thông tin trên đã chính xác chưa?**"
    ),
    display_mode=ResponseMode.LLM,
    display_llm_prompt=(
        "Rewrite this confirmation message to sound warm, caring, and professionally "
        "supportive—like a medical assistant double-checking important information. "
        "Do *not* change any data fields, numbers, or structure. "
        "Keep all emojis, sections, and formatting exactly as they are. "
        "Just make the tone friendly, reassuring, and clear."
    ),

    # TTS: gọn – dễ nghe – không icon – không format gây ngắt hơi
    tts_message_template=(
        "Tôi xin xác nhận lại thông tin đặt lịch khám tại viện. "
        "Họ tên {name}, số điện thoại {phone}, ngày sinh {birth_date}, giới tính {sex}. "
        "Cơ sở khám {facility_name}, ngày hẹn {appointment_date}, giờ hẹn {appointment_time}. "
        "{optional_info} "
        "Bạn cho tôi biết thông tin này đã chính xác chưa?"
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    priority="normal"
)


CONFIRM_BOOKING_HOME = ResponseTemplate(
    key="confirm_booking_home",
    description="Xác nhận thông tin home visit booking",
    variables=[
        "name", "phone", "birth_date", "sex",
        "address", "appointment_date",
        "appointment_time", "reason"
    ],

    # DISPLAY (LLM rewrite: warm, medical-friendly, không đổi cấu trúc)
    display_template=(
        "📋 **Xác nhận thông tin đặt lịch khám tại nhà**\n\n"
        "👤 **Họ tên:** {name}\n"
        "📞 **Số điện thoại:** {phone}\n"
        "🎂 **Ngày sinh:** {birth_date}\n"
        "⚧ **Giới tính:** {sex}\n"
        "🏠 **Địa chỉ:** {address}\n"
        "📅 **Ngày hẹn:** {appointment_date}\n"
        "🕐 **Giờ hẹn:** {appointment_time}\n"
        "📝 **Lý do khám:** {reason}\n"
        "\n**Thông tin trên đã chính xác chưa?**"
    ),
    display_mode=ResponseMode.LLM,
    display_llm_prompt=(
        "Rewrite this confirmation message so it sounds warm, supportive, "
        "and professionally caring — like a medical assistant calmly "
        "double-checking details for a home visit appointment. "
        "Do not change any structure, fields, emojis, or formatting. "
        "Only adjust the wording to be friendly and reassuring."
    ),

    # TTS — gọn, không icon, không ký tự gây ngắt
    tts_message_template=(
        "Tôi xin xác nhận lại thông tin đặt lịch khám tại nhà. "
        "Họ tên {name}, số điện thoại {phone}, ngày sinh {birth_date}, giới tính {sex}. "
        "Địa chỉ {address}. "
        "Ngày hẹn {appointment_date}, giờ hẹn {appointment_time}. "
        "Lý do khám {reason}. "
        "Bạn cho tôi biết thông tin này đã chính xác chưa?"
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


CONFIRM_BOOKING_TEST = ResponseTemplate(
    key="confirm_booking_test",
    description="Xác nhận thông tin test at home booking",
    variables=[
        "name", "phone", "birth_date", "sex",
        "address", "appointment_date", "appointment_time"
    ],

    # DISPLAY (LLM rewrite: warm, caring, giữ nguyên structure & icons)
    display_template=(
        "📋 **Xác nhận thông tin đặt lịch xét nghiệm tại nhà**\n\n"
        "👤 **Họ tên:** {name}\n"
        "📞 **Số điện thoại:** {phone}\n"
        "🎂 **Ngày sinh:** {birth_date}\n"
        "⚧ **Giới tính:** {sex}\n"
        "🏠 **Địa chỉ:** {address}\n"
        "📅 **Ngày hẹn:** {appointment_date}\n"
        "🕐 **Giờ hẹn:** {appointment_time}\n"
        "\n**Thông tin trên đã chính xác chưa?**"
    ),
    display_mode=ResponseMode.LLM,
    display_llm_prompt=(
        "Rewrite this message to make it warm, gentle, and professionally supportive. "
        "Write as if you are a helpful medical assistant double-checking appointment details. "
        "Do not change any structure, emojis, fields, or formatting. "
        "Only improve tone and clarity."
    ),

    # TTS — clear, smooth, no icons
    tts_message_template=(
        "Tôi xin xác nhận lại thông tin đặt lịch xét nghiệm tại nhà. "
        "Họ tên {name}, số điện thoại {phone}, ngày sinh {birth_date}, giới tính {sex}. "
        "Địa chỉ {address}. "
        "Ngày hẹn {appointment_date}, giờ hẹn {appointment_time}. "
        "Bạn cho tôi biết thông tin này đã chính xác chưa?"
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


# ==================== SUCCESS/ERROR ====================

BOOKING_SUCCESS = ResponseTemplate(
    key="booking_success",
    description="Thông báo đặt lịch thành công",
    variables=["appointment_id"],

    # DISPLAY: Giữ mã lịch hẹn, bold rõ ràng
    display_template=(
        "✅ **Đặt lịch thành công!**\n\n"
        "Mã lịch hẹn của bạn là: **{appointment_id}**\n\n"
        "Nhân viên sẽ liên hệ bạn sớm để xác nhận."
    ),
    display_mode=ResponseMode.TEMPLATE,

    # TTS: Không đọc mã, giọng tự nhiên – ngắn gọn – chuyên nghiệp
    tts_message_template=(
        "Đặt lịch thành công. "
        "Nhân viên sẽ sớm liên hệ với bạn để xác nhận lại thông tin."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


BOOKING_CANCELLED = ResponseTemplate(
    key="booking_cancelled",
    display_template=(
        "Đã hủy đặt lịch. Nếu bạn cần hỗ trợ gì khác, vui lòng cho mình biết nhé! 😊"
    ),
    display_mode=ResponseMode.TEMPLATE,   # thêm
    tts_message_template=(
        "Đã hủy đặt lịch. Nếu bạn cần hỗ trợ gì khác, vui lòng cho mình biết nhé!"
    ),
    tts_message_mode=ResponseMode.TEMPLATE,  # thêm
    description="Thông báo hủy đặt lịch",
    variables=[]
)


# ==================== EDGE CASE: INTENT/METHOD SWITCH ====================

BOOKING_INTENT_SWITCH_AFTER_SUBMIT = ResponseTemplate(
    key="booking_intent_switch_after_submit",
    display_template=(
        "⚠️ Bạn đã đặt lịch **{old_intent}** thành công rồi.\n\n"
        "Để đổi sang **{new_intent}**, bạn cần:\n"
        "1. Hủy lịch đã đặt\n"
        "2. Đặt lịch mới với hình thức {new_intent}\n\n"
        "Bạn có muốn mình hướng dẫn hủy lịch không? 🤔"
    ),
    display_mode=ResponseMode.TEMPLATE,   # thêm
    tts_message_template=(
        "Bạn đã đặt lịch {old_intent} thành công rồi. "
        "Để đổi sang {new_intent}, bạn cần hủy lịch đã đặt và đặt lịch mới. "
        "Bạn có muốn mình hướng dẫn hủy lịch không?"
    ),
    tts_message_mode=ResponseMode.TEMPLATE,  # thêm
    description="Thông báo không thể đổi intent sau khi submit",
    variables=["old_intent", "new_intent"],
    priority="high"
)


# ==================== FIELD CORRECTION ====================

ASK_WHICH_FIELD_TO_CORRECT = ResponseTemplate(
    key="ask_which_field_to_correct",
    display_template=(
        "🔧 **Bạn muốn chỉnh sửa thông tin nào?**\n\n"
        "{fields}\n\n"
        "Bạn hãy cho mình biết mục cần sửa nhé!"
    ),
    display_mode=ResponseMode.TEMPLATE,
    tts_message_template=(
        "Bạn muốn chỉnh sửa thông tin nào? "
        "{fields}. "
        "Bạn cho mình biết mục bạn muốn sửa nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,
    description="Hỏi người dùng muốn sửa trường nào",
    variables=["fields"]
)


BOOKING_ERROR = ResponseTemplate(
    key="booking_error",
    display_template=(
        "❌ **Rất tiếc, đã xảy ra lỗi khi xử lý yêu cầu đặt lịch.**\n\n"
        "Chi tiết lỗi: {error_message}\n\n"
        "Bạn vui lòng thử lại sau hoặc liên hệ hotline để được hỗ trợ nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,
    tts_message_template=(
        "Rất tiếc, đã xảy ra lỗi khi xử lý yêu cầu đặt lịch. "
        "Chi tiết lỗi: {error_message}. "
        "Bạn vui lòng thử lại sau hoặc liên hệ hotline để được hỗ trợ."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,
    description="Thông báo lỗi",
    variables=["error_message"]
)


ERROR_MISSING_PROVINCE = ResponseTemplate(
    key="error_missing_province",
    display_template=(
        "❌ **Mình chưa xác định được tỉnh hoặc thành phố của bạn.**\n\n"
        "Bạn vui lòng cung cấp lại giúp mình tên tỉnh/thành phố để mình hỗ trợ tiếp nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,
    tts_message_template=(
        "Mình chưa xác định được tỉnh hoặc thành phố của bạn. "
        "Bạn vui lòng nói lại giúp mình tên tỉnh hoặc thành phố để mình hỗ trợ tiếp."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,
    description="Lỗi thiếu thông tin tỉnh/thành phố",
    variables=[]
)


# Validation error templates
VALIDATION_ERROR_NAME = ResponseTemplate(
    key="validation_error_name",
    display_template=(
        "❌ **{error_message}**\n\n"
        "Bạn vui lòng cung cấp lại **họ và tên đầy đủ** nhé "
        "(ví dụ: *Nguyễn Văn A*)."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "{error_message}. "
        "Bạn vui lòng cung cấp lại họ và tên đầy đủ, ví dụ như Nguyễn Văn A."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    description="Lỗi validation tên",
    variables=["error_message"]
)

VALIDATION_ERROR_BIRTH_DATE = ResponseTemplate(
    key="validation_error_birth_date",
    display_template=(
        "❌ **{error_message}**\n\n"
        "Bạn vui lòng cung cấp lại **ngày sinh** theo đúng định dạng nhé "
        "(ví dụ: *15/03/1990* hoặc *1990-03-15*)."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "{error_message}. "
        "Bạn vui lòng cung cấp lại ngày sinh theo đúng định dạng ngày tháng năm."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    description="Lỗi validation ngày sinh",
    variables=["error_message"]
)


VALIDATION_ERROR_SEX = ResponseTemplate(
    key="validation_error_sex",
    display_template=(
        "❌ **{error_message}**\n\n"
        "Bạn vui lòng chọn một trong các giới tính sau nhé: **Nam**, **Nữ**, hoặc **Khác**."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "{error_message}. "
        "Bạn vui lòng chọn giới tính Nam, Nữ, hoặc Khác."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    description="Lỗi validation giới tính",
    variables=["error_message"]
)


VALIDATION_ERROR_ADDRESS = ResponseTemplate(
    key="validation_error_address",
    description="Lỗi validation địa chỉ",
    variables=["error_message"],

    display_template=(
        "❌ **{error_message}**\n\n"
        "Bạn vui lòng cung cấp **địa chỉ đầy đủ và chi tiết** nhé "
        "(ví dụ: *123 Nguyễn Trãi, Phường 1*)."
    ),


    tts_message_template=(
        "{error_message}. "
        "Bạn vui lòng cung cấp địa chỉ đầy đủ và chi tiết."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


VALIDATION_ERROR_EMAIL = ResponseTemplate(
    key="validation_error_email",
    description="Lỗi validation email",
    variables=["error_message"],

    display_template=(
        "❌ **{error_message}**\n\n"
        "Bạn vui lòng cung cấp **email đúng định dạng** nhé "
        "(ví dụ: *example@domain.com*)."
    ),

    tts_message_template=(
        "{error_message}. "
        "Bạn vui lòng cung cấp email đúng định dạng."
    ),

    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


CONFIRM_INFO_PREFIX = ResponseTemplate(
    key="confirm_info_prefix",
    description="Tiền tố cho phần xác nhận thông tin",
    variables=[],

    display_template=(
        "🔎 **Để đảm bảo thông tin chính xác**, bạn vui lòng kiểm tra và xác nhận lại giúp mình:\n\n"
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Để đảm bảo thông tin chính xác, bạn vui lòng kiểm tra và xác nhận lại giúp mình."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


# ==================== MANAGEMENT FLOW ====================

# Ask for information
MANAGEMENT_ASK_PHONE = ResponseTemplate(
    key="management_ask_phone",
    description="Hỏi số điện thoại để tra cứu",
    variables=[],

    display_template=(
        "🔎 Để mình hỗ trợ **tra cứu lịch hẹn**, bạn vui lòng cho mình biết "
        "**số điện thoại** đã dùng khi đặt lịch nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Để hỗ trợ tra cứu lịch hẹn, bạn vui lòng cung cấp số điện thoại đã dùng khi đặt lịch."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


MANAGEMENT_ASK_PHONE_INVALID = ResponseTemplate(
    key="management_ask_phone_invalid",
    description="Thông báo SĐT không hợp lệ",
    variables=["error_message"],

    display_template=(
        "❌ **{error_message}**\n\n"
        "Bạn vui lòng nhập **số điện thoại hợp lệ** nhé "
        "(10 số và bắt đầu bằng **0**)."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "{error_message}. "
        "Bạn vui lòng cung cấp số điện thoại hợp lệ, gồm 10 số và bắt đầu bằng số 0."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


MANAGEMENT_ASK_SELECTION = ResponseTemplate(
    key="management_ask_selection",
    description="Hỏi chọn lịch hẹn",
    variables=[],

    display_template=(
        "📋 Bạn muốn thao tác với **lịch hẹn số mấy**?\n\n"
        "Vui lòng cho mình biết **số thứ tự** tương ứng nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Bạn muốn thao tác với lịch hẹn nào? "
        "Vui lòng cho mình biết số thứ tự tương ứng."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


MANAGEMENT_ASK_NEW_DATETIME = ResponseTemplate(
    key="management_ask_new_datetime",
    description="Hỏi thời gian mới",
    variables=[],

    display_template=(
        "⏰ Bạn muốn **đổi sang thời gian nào**?\n\n"
        "VD: **15/01/2025 09:00**"
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Bạn muốn đổi sang thời gian nào? "
        "Ví dụ: ngày mười lăm tháng một năm hai nghìn không trăm hai mươi lăm, lúc chín giờ sáng."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


# Search results
MANAGEMENT_NO_APPOINTMENTS = ResponseTemplate(
    key="management_no_appointments",
    display_template="Không tìm thấy lịch hẹn nào với số điện thoại này.",
    tts_message_template="Không tìm thấy lịch hẹn nào với số điện thoại này.",
    description="Không có lịch hẹn",
    variables=[],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)



MANAGEMENT_APPOINTMENT_LIST = ResponseTemplate(
    key="management_appointment_list",
    display_template=(
        "🔍 Tôi tìm thấy các lịch hẹn sau:\n"
        "{appointments}\n\n"
        "Bạn muốn **hủy** hay **thay đổi** lịch nào? "
        "Vui lòng cho tôi biết **số thứ tự**."
    ),
    tts_message_template=(
        "Tôi tìm thấy các lịch hẹn sau: {appointments}. "
        "Bạn muốn hủy hay thay đổi lịch nào? "
        "Vui lòng cho tôi biết số thứ tự."
    ),
    description="Hiển thị danh sách lịch hẹn tìm được và yêu cầu chọn thao tác",
    variables=["appointments"],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


# ==================== FACILITY & SPECIALIST SELECTION ====================

FACILITY_SELECTION = ResponseTemplate(
    key="facility_selection",
    display_template=(
        "Bạn muốn khám tại cơ sở nào? Dưới đây là một số cơ sở tại **{province_name}**:\n\n"
        "{facilities}\n\n"
        "Vui lòng nhập **tên cơ sở** hoặc **số thứ tự** để chọn."
    ),
    tts_message_template=(
        "Bạn muốn khám tại cơ sở nào? "
        "Dưới đây là một số cơ sở tại {province_name}. "
        "{facilities}. "
        "Vui lòng nhập tên cơ sở hoặc số thứ tự để chọn."
    ),
    description="Hiển thị danh sách cơ sở để người dùng chọn",
    variables=["province_name", "facilities"],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


FACILITY_NOT_FOUND = ResponseTemplate(
    key="facility_not_found",
    display_template=(
        "❌ Không tìm thấy cơ sở phù hợp tại **{province_name}**.\n\n"
        "Vui lòng chọn tỉnh/thành phố khác."
    ),
    tts_message_template=(
        "Không tìm thấy cơ sở phù hợp tại {province_name}. "
        "Vui lòng chọn tỉnh hoặc thành phố khác."
    ),
    description="Không tìm thấy cơ sở tại tỉnh/thành phố",
    variables=["province_name"],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


SPECIALIST_SELECTION = ResponseTemplate(
    key="specialist_selection",
    display_template=(
        "📋 **Danh sách chuyên khoa:**\n"
        "{specialists}\n\n"
        "✍️ Vui lòng trả lời theo mẫu:\n"
        "**\"Lý do: [lý do], Chuyên khoa: [số hoặc tên]\"**\n\n"
        "Ví dụ:\n"
        "- \"Lý do: Đau đầu, Chuyên khoa: 5\"\n"
        "- \"Lý do: Khám sức khỏe\" (nếu không chọn chuyên khoa)"
    ),
    tts_message_template=(
        "Sau đây là danh sách các chuyên khoa: {specialists}. "
        "Bạn vui lòng trả lời theo mẫu: Lý do ... và Chuyên khoa ... "
        "Ví dụ: Lý do đau đầu, chuyên khoa số 5. "
        "Hoặc: Lý do khám sức khỏe nếu bạn không muốn chọn chuyên khoa."
    ),
    description="Hiển thị danh sách chuyên khoa để người dùng lựa chọn",
    variables=["specialists"],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


# Success messages
MANAGEMENT_CANCEL_SUCCESS = ResponseTemplate(
    key="management_cancel_success",
    display_template=(
        "✅ Lịch hẹn của bạn đã được hủy thành công!\n"
        "Mã lịch hẹn: **{appointment_id}**"
    ),
    display_mode=ResponseMode.TEMPLATE,   # hoặc "replace" tùy workflow của bạn

    tts_message_template=(
        "Lịch hẹn của bạn đã được hủy thành công."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,  # TTS không cần đọc mã lịch hẹn

    description="Thông báo hủy lịch thành công (mã lịch hẹn chỉ hiển thị ở UI)",
    variables=["appointment_id"]
)


MANAGEMENT_UPDATE_SUCCESS = ResponseTemplate(
    key="management_update_success",
    display_template=(
        "✅ Lịch hẹn mã **{appointment_id}** đã được cập nhật sang thời gian "
        "**{new_time}** thành công!"
    ),
    display_mode=ResponseMode.TEMPLATE,   # hoặc "replace" tùy logic workflow

    tts_message_template=(
        "Lịch hẹn của bạn đã được cập nhật sang thời gian mới là {new_time}."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    description="Thông báo cập nhật lịch hẹn thành công",
    variables=["appointment_id", "new_time"]
)


# Error messages
MANAGEMENT_SEARCH_FAILED = ResponseTemplate(
    key="management_search_failed",
    display_template=(
        "❌ Hiện tại không thể tra cứu lịch hẹn. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Hiện tại không thể tra cứu lịch hẹn. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    description="Lỗi tra cứu lịch hẹn",
    variables=[]
)


MANAGEMENT_CANCEL_FAILED = ResponseTemplate(
    key="management_cancel_failed",
    display_template=(
        "❌ Rất tiếc, mình chưa thể hủy lịch hẹn lúc này. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Rất tiếc, mình chưa thể hủy lịch hẹn lúc này. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    description="Lỗi hủy lịch",
    variables=[]
)


MANAGEMENT_UPDATE_FAILED = ResponseTemplate(
    key="management_update_failed",
    display_template=(
        "❌ Rất tiếc, hiện tại mình chưa thể cập nhật lịch hẹn cho bạn. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Rất tiếc, hiện tại mình chưa thể cập nhật lịch hẹn cho bạn. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,

    description="Lỗi cập nhật lịch",
    variables=[]
)


MANAGEMENT_API_ERROR = ResponseTemplate(
    key="management_api_error",
    description="Lỗi API với message cụ thể",
    variables=["error_message"],

    display_template=(
        "❌ Đã xảy ra lỗi khi xử lý yêu cầu: {error_message}\n\n"
        "Bạn vui lòng thử lại sau nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Đã xảy ra lỗi khi xử lý yêu cầu. {error_message}. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


MANAGEMENT_APPOINTMENT_DETAIL_ERROR = ResponseTemplate(
    key="management_appointment_detail_error",
    description="Lỗi lấy chi tiết lịch hẹn",
    variables=["error_message"],

    display_template=(
        "❌ Không thể lấy chi tiết lịch hẹn: {error_message}\n\n"
        "Bạn vui lòng thử lại sau nhé."
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Không thể lấy chi tiết lịch hẹn. {error_message}. "
        "Bạn vui lòng thử lại sau nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


# ==================== BOOKING SUCCESS MESSAGES ====================

QUICK_BOOKING_SUCCESS = ResponseTemplate(
    key="quick_booking_success",
    description="Thông báo đặt lịch nhanh thành công",
    variables=["appointment_id"],

    # UI hiển thị: GIỮ mã lịch hẹn
    display_template=(
        "✅ Đặt lịch NHANH thành công!\n\n"
        "Mã lịch hẹn: **{appointment_id}**\n\n"
        "Nhân viên Medlatec sẽ sớm liên hệ với bạn để xác nhận chi tiết."
    ),
    display_mode=ResponseMode.TEMPLATE,

    # TTS: bỏ mã lịch hẹn (như yêu cầu)
    tts_message_template=(
        "Đặt lịch nhanh thành công. "
        "Nhân viên Medlatec sẽ sớm liên hệ với bạn để xác nhận chi tiết."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


DETAILED_BOOKING_SUCCESS = ResponseTemplate(
    key="detailed_booking_success",
    description="Thông báo đặt lịch chi tiết thành công",
    variables=["appointment_id"],

    # Display: GIỮ mã lịch hẹn
    display_template=(
        "✅ Đặt lịch CHI TIẾT thành công!\n\n"
        "Mã lịch hẹn: **{appointment_id}**\n\n"
        "Vui lòng kiểm tra email/SMS để xem chi tiết lịch hẹn."
    ),
    display_mode=ResponseMode.TEMPLATE,

    # TTS: BỎ mã lịch hẹn
    tts_message_template=(
        "Đặt lịch chi tiết thành công. "
        "Vui lòng kiểm tra email hoặc tin nhắn SMS để xem chi tiết lịch hẹn."
    ),
    tts_message_mode=ResponseMode.TEMPLATE
)


# ==================== GENERAL CHAT & SYSTEM MESSAGES ====================

GREETING_DEFAULT = ResponseTemplate(
    key="greeting_default",
    description="Lời chào mặc định",
    variables=[],

    display_template="Xin chào! Tôi có thể giúp gì cho bạn?",
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template="Xin chào! Tôi có thể giúp gì cho bạn?",
    tts_message_mode=ResponseMode.TEMPLATE
)


GENERAL_CHAT_ERROR = ResponseTemplate(
    key="general_chat_error",
    description="Lỗi khi general chat",
    variables=[],

    display_template="Xin lỗi, tôi đang gặp chút vấn đề. Bạn vui lòng thử lại giúp mình nhé!",
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template="Xin lỗi, tôi đang gặp chút vấn đề. Bạn vui lòng thử lại giúp mình nhé.",
    tts_message_mode=ResponseMode.TEMPLATE
)


# ==================== ROUTER & STATUS MESSAGES ====================

INVALID_INTENT = ResponseTemplate(
    key="invalid_intent",
    description="Không xác định được intent",
    variables=[],

    display_template=(
        "❌ Mình chưa xác định được hình thức đặt lịch bạn muốn.\n"
        "Bạn có thể mô tả rõ hơn để mình hỗ trợ chính xác nhé!"
    ),
    display_mode=ResponseMode.TEMPLATE,

    tts_message_template=(
        "Mình chưa xác định được hình thức đặt lịch bạn muốn. "
        "Bạn có thể nói rõ hơn để mình hỗ trợ chính xác nhé."
    ),
    tts_message_mode=ResponseMode.TEMPLATE,
)


PROCESSING = ResponseTemplate(
    key="processing",
    display_template="⏳ Đang xử lý thông tin của bạn...",
    tts_message_template="Đang xử lý thông tin của bạn.",
    description="Thông báo cho người dùng biết hệ thống đang xử lý",
    variables=[],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


# ==================== SYSTEM ERROR MESSAGES ====================

SESSION_NOT_FOUND = ResponseTemplate(
    key="session_not_found",
    display_template="❌ Không tìm thấy session_id. Vui lòng thử lại.",
    tts_message_template="Không tìm thấy mã phiên làm việc. Vui lòng thử lại.",
    description="Lỗi không tìm thấy hoặc thiếu session_id trong request.",
    variables=[],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


EMPTY_MESSAGE = ResponseTemplate(
    key="empty_message",
    display_template="❌ Tôi không nhận được nội dung tin nhắn. Vui lòng thử lại.",
    tts_message_template="Tôi không nhận được nội dung tin nhắn. Vui lòng thử lại.",
    description="Lỗi: người dùng gửi tin nhắn rỗng hoặc không hợp lệ.",
    variables=[],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)


GENERAL_ERROR = ResponseTemplate(
    key="general_error",
    display_template="❌ Đã xảy ra lỗi. Vui lòng thử lại sau.",
    tts_message_template="Đã xảy ra lỗi. Vui lòng thử lại sau.",
    description="Lỗi chung không xác định.",
    variables=[],
    tts_message_mode=ResponseMode.TEMPLATE,
    display_mode=ResponseMode.TEMPLATE,
)

# ==================== FIELD NAME MAPPING ====================

FIELD_DISPLAY_NAMES: Dict[str, str] = {
    "name": "Tên",
    "phone": "Số điện thoại",
    "method_type": "Hình thức khám",
    "user_intent": "Loại đặt lịch",
    "birth_date": "Ngày sinh",
    "sex": "Giới tính",
    "address": "Địa chỉ",
    "province": "Tỉnh/Thành phố",
    "ward": "Phường/Xã",
    "facility": "Cơ sở y tế",
    "appointment_date": "Ngày hẹn",
    "work_time_test": "Giờ hẹn",
    "reason_note": "Lý do khám",
    "specialist_id": "Chuyên khoa",
}

METHOD_TYPE_DISPLAY_NAMES: Dict[str, str] = {
    "HOSPITAL": "Tại viện",
    "HOME": "Tại nhà",
    "TEST_AT_HOME": "Xét nghiệm tại nhà",
}

SEX_DISPLAY_NAMES: Dict[str, str] = {
    "MALE": "Nam",
    "FEMALE": "Nữ",
    "OTHER": "Khác",
}

# ==================== HELPER FUNCTIONS ====================

def get_field_display_name(field_key: str) -> str:
    """Get Vietnamese display name for field."""
    return FIELD_DISPLAY_NAMES.get(field_key, field_key)


def get_method_display_name(method_type: str) -> str:
    """Get Vietnamese display name for method type."""
    return METHOD_TYPE_DISPLAY_NAMES.get(method_type, method_type)


def get_sex_display_name(sex: str) -> str:
    """Get Vietnamese display name for sex."""
    return SEX_DISPLAY_NAMES.get(sex, sex)


def clean_markdown(text: str) -> str:
    """
    Remove markdown formatting for tts_message.
    
    Cleans text to make it suitable for voice reading:
    - Removes **bold** and *italic* markers
    - Removes headers (###)
    - Removes links [text](url)
    - Removes list markers (-, *)
    - Removes emojis
    - Normalizes whitespace
    
    Args:
        text: Text with markdown formatting
        
    Returns:
        Clean text suitable for voice reading
    """
    # Remove **bold**
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Remove *italic*
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # Remove headers ###
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove list markers - and *
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    # Remove emojis
    text = re.sub(r'[✅❌🔍📋💡⏳🎉👋]', '', text)
    # Convert newlines to periods for better speech flow
    text = re.sub(r'\n+', '. ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def prepare_response_config(
        template_key: str,
        variables: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Prepare response configuration for generating response.

    This config is used when routing to generate_final_answer node
    or for generating template-based responses.

    Args:
        template_key: Key of the response template
        variables: Variables to fill in template

    Returns:
        Config dict with all necessary info for response generation

    Raises:
        ValueError: If template_key not found
    """

    logger.debug(
        "prepare_response_config called with template_key=%s, variables=%s",
        template_key, variables
    )

    template = RESPONSE_TEMPLATES.get(template_key)
    if not template:
        logger.error("Template not found for key: %s", template_key)
        raise ValueError(f"Template not found: {template_key}")

    logger.info("Template '%s' found. Preparing response config...", template_key)

    config = {
        "template_key": template_key,
        "variables": variables,
        "display_mode": template.display_mode.value,
        "tts_message_mode": template.tts_message_mode.value,
        "display_template": template.display_template,
        "display_llm_prompt": template.display_llm_prompt,
        "tts_message_template": template.tts_message_template,
        "tts_message_llm_prompt": template.tts_message_llm_prompt,
        "priority": template.priority
    }

    logger.debug(
        "Response config prepared for template_key=%s: %s",
        template_key, config
    )

    logger.info("Response config preparation completed for template_key=%s", template_key)

    return config


def generate_template_response(
    template_key: str,
    variables: Dict[str, Any]
) -> Dict[str, str]:
    """
    Generate response using template mode (both outputs).
    
    Fast path for templates that don't need LLM enhancement.
    Both display and tts_message must be in template mode.
    
    Args:
        template_key: Key of the response template
        variables: Variables to fill in template
        
    Returns:
        Dict with display_message and tts_message
        
    Raises:
        ValueError: If template not found or not in template mode
    """
    template = RESPONSE_TEMPLATES.get(template_key)
    if not template:
        raise ValueError(f"Template not found: {template_key}")
    
    if template.display_mode != ResponseMode.TEMPLATE:
        raise ValueError(
            f"Template {template_key} display_mode is {template.display_mode.value}, not template"
        )
    
    if template.tts_message_mode != ResponseMode.TEMPLATE:
        raise ValueError(
            f"Template {template_key} tts_message_mode is {template.tts_message_mode.value}, not template"
        )
    
    return {
        "display_message": template.format_display(**variables),
        "tts_message": template.format_tts_message(**variables)
    }


def should_use_llm_response(template_key: str) -> bool:
    """
    Check if template needs LLM enhancement.
    
    Quick helper for nodes to decide routing:
    - True: Route to generate_final_answer via Command
    - False: Use template directly (fast path)
    
    Args:
        template_key: Key of the response template
        
    Returns:
        True if ANY output needs LLM enhancement
    """
    template = RESPONSE_TEMPLATES.get(template_key)
    if not template:
        return False
    return template.needs_llm()


def create_response_command(
    template_key: str,
    variables: Dict[str, Any],
    state_updates: Optional[Dict[str, Any]] = None
):
    """
    Create Command to route to generate_final_answer node.
    
    Use this when template.needs_llm() == True.
    
    Args:
        template_key: Key of the response template
        variables: Variables for template formatting
        state_updates: Additional state updates (optional)
        
    Returns:
        Command object to route to generate_final_answer
    """
    from langgraph.types import Command
    
    response_config = prepare_response_config(template_key, variables)
    
    update_dict = {
        "response_config": response_config,
        
    }
    
    # Merge additional state updates (but NOT messages - they'll be generated)
    if state_updates:
        # Pop messages to avoid overwriting response (similar to template path)
        state_updates_copy = state_updates.copy()
        state_updates_copy.pop("messages", None)
        state_updates_copy.pop("is_final_response", None)
        update_dict.update(state_updates_copy)
    
    return Command(
        goto="generate_final_answer",
        update=update_dict
    )


def create_template_response(
    template_key: str,
    variables: Dict[str, Any],
    state_updates: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create immediate template response (fast path).
    
    Use this when template.needs_llm() == False.
    
    Args:
        template_key: Key of the response template
        variables: Variables for template formatting
        state_updates: Additional state updates (optional)
        
    Returns:
        State update dict with AIMessage
    """
    from langchain_core.messages import AIMessage
    
    result = generate_template_response(template_key, variables)
    
    update_dict = {
        "messages": [
            AIMessage(
                content=result["display_message"],
                additional_kwargs={
                    "tts_message": result["tts_message"]
                }
            )
        ],
        
    }
    
    # Merge additional state updates (but preserve messages/is_final_response)
    if state_updates:
        # Create copy to avoid mutating original
        state_updates_copy = state_updates.copy()
        # Remove keys that should not overwrite template response
        state_updates_copy.pop("messages", None)
        state_updates_copy.pop("is_final_response", None)
        # Merge remaining fields
        update_dict.update(state_updates_copy)
    
    return update_dict


def smart_response(
    template_key: str,
    variables: Optional[Dict[str, Any]] = None,
    state_updates: Optional[Dict[str, Any]] = None
):
    """
    Smart response router - automatically chooses between template and LLM.
    
    ONE function to rule them all! Use this in nodes for automatic routing:
    - If template needs LLM: Returns Command to generate_final_answer
    - If template-only: Returns state dict with AIMessage
    
    Example usage in node:
        return smart_response("confirm_booking_hospital", 
                            variables={"name": "Nguyễn Văn A", ...},
                            state_updates={**state, "form": form})
    
    Args:
        template_key: Key of the response template
        variables: Variables for template formatting (optional)
        state_updates: Additional state to merge (optional)
        
    Returns:
        Command (if LLM needed) or Dict (if template-only)
    """
    if variables is None:
        variables = {}
    
    if should_use_llm_response(template_key):
        # LLM path: Route to generate_final_answer
        return create_response_command(template_key, variables, state_updates)
    else:
        # Template path: Generate immediately (already handles state_updates safely)
        return create_template_response(template_key, variables, state_updates)


def format_missing_fields(fields: List[str]) -> str:
    """
    Format list of missing fields to Vietnamese display.
    
    Args:
        fields: List of field keys (e.g., ["name", "phone"])
    
    Returns:
        Formatted string (e.g., "Tên, SĐT, Hình thức khám")
    """
    display_names = [get_field_display_name(f) for f in fields]
    return ", ".join(display_names)


# ==================== RESPONSE REGISTRY ====================

RESPONSE_TEMPLATES: Dict[str, ResponseTemplate] = {
    "ask_basic_missing": ASK_BASIC_MISSING,
    "ask_basic_error": ASK_BASIC_ERROR,
    "ask_preference": ASK_PREFERENCE,
    
    # Hospital
    "ask_detailed_hospital_birth_sex": ASK_DETAILED_HOSPITAL_BIRTH_SEX,
    "ask_detailed_hospital_facility": ASK_DETAILED_HOSPITAL_FACILITY,
    "ask_detailed_hospital_datetime": ASK_DETAILED_HOSPITAL_DATETIME,
    "ask_detailed_hospital_reason_specialist": ASK_DETAILED_HOSPITAL_REASON_SPECIALIST,  # DEPRECATED
    "ask_detailed_hospital_reason_with_specialists": ASK_DETAILED_HOSPITAL_REASON_WITH_SPECIALISTS,
    "ask_detailed_hospital_reason_no_specialists": ASK_DETAILED_HOSPITAL_REASON_NO_SPECIALISTS,
    
    # Home
    "ask_detailed_home_birth_sex": ASK_DETAILED_HOME_BIRTH_SEX,
    "ask_detailed_home_address": ASK_DETAILED_HOME_ADDRESS,
    "ask_detailed_home_datetime": ASK_DETAILED_HOME_DATETIME,
    "ask_detailed_home_reason": ASK_DETAILED_HOME_REASON,
    
    # Test
    "ask_detailed_test_birth_sex": ASK_DETAILED_TEST_BIRTH_SEX,
    "ask_detailed_test_address": ASK_DETAILED_TEST_ADDRESS,
    "ask_detailed_test_datetime": ASK_DETAILED_TEST_DATETIME,
    
    # Confirmation
    "confirm_booking_quick": CONFIRM_BOOKING_QUICK,
    "confirm_booking_hospital": CONFIRM_BOOKING_HOSPITAL,
    "confirm_booking_home": CONFIRM_BOOKING_HOME,
    "confirm_booking_test": CONFIRM_BOOKING_TEST,
    "confirm_info_prefix": CONFIRM_INFO_PREFIX,
    
    # Result
    "booking_success": BOOKING_SUCCESS,
    "booking_cancelled": BOOKING_CANCELLED,
    "booking_intent_switch_after_submit": BOOKING_INTENT_SWITCH_AFTER_SUBMIT,
    "booking_error": BOOKING_ERROR,
    "error_missing_province": ERROR_MISSING_PROVINCE,
    
    # Validation errors
    "validation_error_name": VALIDATION_ERROR_NAME,
    "validation_error_birth_date": VALIDATION_ERROR_BIRTH_DATE,
    "validation_error_sex": VALIDATION_ERROR_SEX,
    "validation_error_address": VALIDATION_ERROR_ADDRESS,
    "validation_error_email": VALIDATION_ERROR_EMAIL,
    
    # Management - Ask
    "management_ask_phone": MANAGEMENT_ASK_PHONE,
    "management_ask_phone_invalid": MANAGEMENT_ASK_PHONE_INVALID,
    "management_ask_selection": MANAGEMENT_ASK_SELECTION,
    "management_ask_new_datetime": MANAGEMENT_ASK_NEW_DATETIME,
    
    # Management - Results
    "management_no_appointments": MANAGEMENT_NO_APPOINTMENTS,
    "management_appointment_list": MANAGEMENT_APPOINTMENT_LIST,
    
    # Facility & Specialist Selection
    "facility_selection": FACILITY_SELECTION,
    "facility_not_found": FACILITY_NOT_FOUND,
    "specialist_selection": SPECIALIST_SELECTION,
    
    # Management - Success
    "management_cancel_success": MANAGEMENT_CANCEL_SUCCESS,
    "management_update_success": MANAGEMENT_UPDATE_SUCCESS,
    
    # Management - Errors
    "management_search_failed": MANAGEMENT_SEARCH_FAILED,
    "management_cancel_failed": MANAGEMENT_CANCEL_FAILED,
    "management_update_failed": MANAGEMENT_UPDATE_FAILED,
    "management_api_error": MANAGEMENT_API_ERROR,
    "management_appointment_detail_error": MANAGEMENT_APPOINTMENT_DETAIL_ERROR,
    
    # Booking Success
    "quick_booking_success": QUICK_BOOKING_SUCCESS,
    "detailed_booking_success": DETAILED_BOOKING_SUCCESS,
    
    # General Chat & System
    "greeting_default": GREETING_DEFAULT,
    "general_chat_error": GENERAL_CHAT_ERROR,
    
    # Router & Status
    "invalid_intent": INVALID_INTENT,
    "processing": PROCESSING,
    
    # System Errors
    "session_not_found": SESSION_NOT_FOUND,
    "empty_message": EMPTY_MESSAGE,
    "general_error": GENERAL_ERROR,
}


def get_response(key: str, **kwargs) -> str:
    """
    Get formatted response by key.
    
    Args:
        key: Response template key
        **kwargs: Variables to format template
    
    Returns:
        Formatted message string
    
    Example:
        >>> get_response("ask_basic_missing", missing_fields="Tên, SĐT")
        "Để đặt lịch, tôi cần: Tên, SĐT."
    """
    template = RESPONSE_TEMPLATES.get(key)
    if not template:
        raise ValueError(f"Response template not found: {key}")
    
    return template.format(**kwargs)
