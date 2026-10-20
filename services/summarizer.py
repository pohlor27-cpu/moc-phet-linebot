import re
from datetime import date, timedelta
from typing import List, Dict, Optional
from domain.models import WorkItem, TaskStatus, DailySummaryReport, UserDailySummary

def tag_mentions(text: str) -> str:
    """Prepend @ to user names, assignees, and drivers for LINE group notifications."""
    if not text:
        return text
    # 1. Prefix titles: คุณ, นางสาว, นาง, นาย with @ if not already tagged
    res = re.sub(r'(?<!@)((?:คุณ|นางสาว|นาง|นาย)[ก-๙a-zA-Z]+)', r'@\1', text)
    # 2. Prefix informal honorifics: พี่, น้อง when isolated
    res = re.sub(r'(?<=[(\s|:,])(?<!@)((?:พี่|น้อง)[ก-๙a-zA-Z]+)', r'@\1', res)
    # 3. Format driver prefix (ผขร:)
    res = re.sub(r'ผขร[:\.]\s*(?!@)([ก-๙a-zA-Z]+)', r'ผขร: @\1', res)
    # 4. Clean duplicate @@
    res = re.sub(r'@+', '@', res)
    return res

def thai_sort_key(name: str) -> str:
    """Sort key for Thai and English names, correctly handling Thai leading vowels."""
    if not name:
        return ""
    s = re.sub(r"^[@\s\-\*•]+", "", name).strip()
    # Strip common honorifics for sorting, but keep them in display
    # (คุณ, นาย, นาง, นางสาว, พี่, น้อง)
    stripped = re.sub(r"^(?:คุณ|นาย|นางสาว|นาง|พี่|น้อง)\s*", "", s)
    if stripped:
        s = stripped
    leading_vowels = "เแโใไ"
    if len(s) >= 2 and s[0] in leading_vowels:
        return s[1] + s[0] + s[2:]
    return s.lower()

def extract_person_name(item: WorkItem) -> str:
    uname = (item.user_name or "").strip()
    if uname and uname not in ["Anonymous", "น้องบอท", "api_tester", "unknown_user", "ผู้ใช้"]:
        return uname
    # Try extracting person name from task text if user_name is generic
    m = re.search(r'[@\(\[]\s*((?:คุณ|นาย|นางสาว|นาง|พี่|น้อง)[ก-๙a-zA-Z]+)', item.task_text)
    if m:
        return m.group(1).strip()
    return uname or "ส่วนกลาง / ไม่ระบุชื่อ"

class DailySummarizer:
    @staticmethod
    def generate_daily_report(items: List[WorkItem], target_date: Optional[date] = None) -> DailySummaryReport:
        if target_date is None:
            target_date = date.today()

        today = date.today()
        date_label = "วันนี้" if target_date == today else ("เมื่อวาน" if target_date == today - timedelta(days=1) else target_date.strftime('%d/%m/%Y'))

        if not items:
            formatted_msg = (
                f"📊 น้องบอทสรุปผลงานประจำ{date_label} ({target_date.strftime('%d/%m/%Y')})\n"
                f"สำนักงานพาณิชย์จังหวัดเพชรบุรี\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ ยังไม่มีรายการงานที่บันทึกไว้สำหรับ{date_label}ครับผม\n\n"
                f"💡 สามารถส่งรูปภาพตารางงานหรือไฟล์ PDF เพื่อบันทึกงานได้ตลอดเวลาครับ"
            )
            return DailySummaryReport(
                report_date=target_date,
                total_users=0,
                total_tasks=0,
                completed_count=0,
                in_progress_count=0,
                blocker_count=0,
                user_summaries=[],
                formatted_line_message=formatted_msg
            )

        # 1. Group items by Person Name
        persons_map: Dict[str, List[WorkItem]] = {}
        for item in items:
            pname = extract_person_name(item)
            if pname not in persons_map:
                persons_map[pname] = []
            persons_map[pname].append(item)

        # 2. Sort persons alphabetically (ชื่อเรียงตามลำดับตัวอักษร)
        sorted_person_names = sorted(persons_map.keys(), key=thai_sort_key)

        # 3. Sort tasks chronologically by date and scheduled_time for each person
        def task_sort_key(it: WorkItem):
            d = it.log_date or date.min
            t = it.scheduled_time or ""
            return (d, t, it.id or 0)

        user_summaries: List[UserDailySummary] = []
        total_tasks = len(items)
        completed_count = sum(1 for it in items if it.status == TaskStatus.DONE)
        in_progress_count = sum(1 for it in items if it.status == TaskStatus.IN_PROGRESS)
        blocker_count = sum(1 for it in items if it.status == TaskStatus.BLOCKER)

        msg_lines = [
            f"📊 น้องบอทสรุปผลงานประจำ{date_label} ({target_date.strftime('%d/%m/%Y')})",
            f"สำนักงานพาณิชย์จังหวัดเพชรบุรี",
            f"━━━━━━━━━━━━━━━━━━",
            f"📝 รวมทั้งหมด {total_tasks} ภารกิจ ({len(sorted_person_names)} ท่าน)",
            f"━━━━━━━━━━━━━━━━━━\n"
        ]

        for pname in sorted_person_names:
            person_items = sorted(persons_map[pname], key=task_sort_key)
            
            done_list = [it.task_text for it in person_items if it.status == TaskStatus.DONE]
            prog_list = [it.task_text for it in person_items if it.status == TaskStatus.IN_PROGRESS]
            block_list = [it.task_text for it in person_items if it.status == TaskStatus.BLOCKER]
            note_list = [it.task_text for it in person_items if it.status == TaskStatus.NOTE]

            user_sum = UserDailySummary(
                user_id=pname,
                user_name=pname,
                total_tasks=len(person_items),
                done_tasks=done_list,
                in_progress_tasks=prog_list,
                blockers=block_list,
                notes=note_list
            )
            user_summaries.append(user_sum)

            msg_lines.append(f"👤 {pname} ({len(person_items)} ภารกิจ):")
            for it in person_items:
                # Format icon by status
                if it.status == TaskStatus.DONE:
                    icon = "✅"
                elif it.status == TaskStatus.IN_PROGRESS:
                    icon = "⏳"
                elif it.status == TaskStatus.BLOCKER:
                    icon = "⚠️"
                else:
                    icon = "📌"

                date_prefix = f"{it.log_date.strftime('%d/%m/%Y')} " if it.log_date else ""
                time_tag = f"[{it.scheduled_time}] " if it.scheduled_time else ""
                tagged_task = tag_mentions(it.task_text.strip())
                msg_lines.append(f"  • {date_prefix}{time_tag}{icon} {tagged_task}")
            msg_lines.append("")

        msg_lines.append("━━━━━━━━━━━━━━━━━━")
        msg_lines.append("💡 พิมพ์ 'พรุ่งนี้' เพื่อดูตารางภารกิจวันพรุ่งนี้ครับผม")

        return DailySummaryReport(
            report_date=target_date,
            total_users=len(sorted_person_names),
            total_tasks=total_tasks,
            completed_count=completed_count,
            in_progress_count=in_progress_count,
            blocker_count=blocker_count,
            user_summaries=user_summaries,
            formatted_line_message="\n".join(msg_lines).strip()
        )


    @staticmethod
    def generate_morning_briefing(items: List[WorkItem], target_date: Optional[date] = None) -> str:
        if target_date is None:
            target_date = date.today()

        today = date.today()
        if target_date == today:
            title_prefix = "☀️ อรุณสวัสดิ์ครับผม! ตารางภารกิจประจำวันนี้"
            empty_prefix = "✨ วันนี้ยังไม่มีกำหนดการหรือตารางงานที่บันทึกไว้ครับ"
        elif target_date == today + timedelta(days=1):
            title_prefix = "📅 ตารางภารกิจประจำวันพรุ่งนี้"
            empty_prefix = "✨ วันพรุ่งนี้ยังไม่มีกำหนดการหรือตารางงานที่บันทึกไว้ครับ"
        else:
            title_prefix = f"📅 ตารางภารกิจประจำวันที่ {target_date.strftime('%d/%m/%Y')}"
            empty_prefix = f"✨ วันที่ {target_date.strftime('%d/%m/%Y')} ยังไม่มีกำหนดการที่บันทึกไว้ครับ"

        if not items:
            return (
                f"{title_prefix} ({target_date.strftime('%d/%m/%Y')})\n"
                f"สำนักงานพาณิชย์จังหวัดเพชรบุรี\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{empty_prefix}\n\n"
                f"💡 สามารถส่งรูปภาพตารางงานเพื่อให้น้องบอทบันทึกข้อมูลได้เลยครับผม!"
            )

        # Deduplicate tasks
        seen = set()
        unique_items = []
        for item in items:
            key = (item.task_text.strip(), item.scheduled_time)
            if key not in seen and item.task_text.strip():
                seen.add(key)
                unique_items.append(item)

        lines = [
            f"{title_prefix} ({target_date.strftime('%d/%m/%Y')})",
            f"สำนักงานพาณิชย์จังหวัดเพชรบุรี",
            f"━━━━━━━━━━━━━━━━━━",
            f"📋 รายการภารกิจทั้งหมด ({len(unique_items)} รายการ):",
            ""
        ]

        for idx, item in enumerate(unique_items[:30], 1):
            time_tag = f"[{item.scheduled_time}] " if item.scheduled_time else ""
            tagged_task = tag_mentions(item.task_text)
            lines.append(f"{idx}. 📌 {time_tag}{tagged_task}")

        if len(unique_items) > 30:
            lines.append(f"\n... และมีรายการอื่นๆ อีก {len(unique_items) - 30} รายการ")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("💪 น้องบอทขอให้ทุกคนทำงานอย่างราบรื่นและมีความสุขตลอดทั้งวันครับผม!")

        return "\n".join(lines).strip()
