from datetime import date
from typing import List, Dict
from domain.models import WorkItem, TaskStatus, DailySummaryReport, UserDailySummary

class DailySummarizer:
    @staticmethod
    def generate_daily_report(items: List[WorkItem], target_date: date = None) -> DailySummaryReport:
        if target_date is None:
            target_date = date.today()

        if not items:
            formatted_msg = (
                f"📊 สรุปรายงานประจำวัน ({target_date.strftime('%d/%m/%Y')})\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"❌ ยังไม่มีการบันทึกรายการงานสำหรับวันนี้\n\n"
                f"💡 สามารถพิมพ์ส่งข้อความ หรือส่งรูปภาพตารางงานได้ตลอดเวลาครับ"
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

        # Deduplicate and group items by user
        users_map: Dict[str, Dict] = {}
        for item in items:
            uid = item.user_id
            uname = item.user_name or "Anonymous"
            if uid not in users_map:
                users_map[uid] = {
                    "name": uname,
                    "done": [],
                    "in_progress": [],
                    "blockers": [],
                    "notes": []
                }
            
            task_clean = item.task_text.strip()
            if not task_clean:
                continue

            target_list = None
            if item.status == TaskStatus.DONE:
                target_list = users_map[uid]["done"]
            elif item.status == TaskStatus.IN_PROGRESS:
                target_list = users_map[uid]["in_progress"]
            elif item.status == TaskStatus.BLOCKER:
                target_list = users_map[uid]["blockers"]
            else:
                target_list = users_map[uid]["notes"]
            
            if task_clean not in target_list:
                target_list.append(task_clean)

        user_summaries: List[UserDailySummary] = []
        total_tasks = len(items)
        completed_count = sum(len(u["done"]) for u in users_map.values())
        in_progress_count = sum(len(u["in_progress"]) for u in users_map.values())
        blocker_count = sum(len(u["blockers"]) for u in users_map.values())

        msg_lines = [
            f"📊 สรุปงานประจำวัน ({target_date.strftime('%d/%m/%Y')})",
            f"━━━━━━━━━━━━━━━━━━",
            f"👥 ผู้รายงาน: {len(users_map)} คน | 📝 รวม {total_tasks} รายการ",
            f"✅ สำเร็จ: {completed_count} | ⏳ กำลังทำ: {in_progress_count} | ⚠️ ปัญหา: {blocker_count}",
            f"━━━━━━━━━━━━━━━━━━\n"
        ]

        for uid, data in users_map.items():
            user_sum = UserDailySummary(
                user_id=uid,
                user_name=data["name"],
                total_tasks=len(data["done"]) + len(data["in_progress"]) + len(data["blockers"]) + len(data["notes"]),
                done_tasks=data["done"],
                in_progress_tasks=data["in_progress"],
                blockers=data["blockers"],
                notes=data["notes"]
            )
            user_summaries.append(user_sum)

            msg_lines.append(f"👤 {data['name']}:")
            if data["done"]:
                msg_lines.append("  ✅ งานที่เสร็จแล้ว:")
                for t in data["done"][:20]:
                    msg_lines.append(f"    • {t}")
                if len(data["done"]) > 20:
                    msg_lines.append(f"    ... และอีก {len(data['done']) - 20} รายการ")

            if data["in_progress"]:
                msg_lines.append("  ⏳ กำลังดำเนินการ:")
                for t in data["in_progress"][:20]:
                    msg_lines.append(f"    • {t}")
                if len(data["in_progress"]) > 20:
                    msg_lines.append(f"    ... และอีก {len(data['in_progress']) - 20} รายการ")

            if data["blockers"]:
                msg_lines.append("  ⚠️ ติดปัญหา/บล็อกเกอร์:")
                for t in data["blockers"][:10]:
                    msg_lines.append(f"    • {t}")

            if data["notes"]:
                msg_lines.append("  📌 บันทึกเพิ่มเติม:")
                for t in data["notes"][:10]:
                    msg_lines.append(f"    • {t}")
            msg_lines.append("")

        msg_lines.append("━━━━━━━━━━━━━━━━━━")
        msg_lines.append("🚀 พิมพ์ 'ตารางงาน' เพื่อดูภารกิจวันนี้ หรือส่งข้อความ/รูปภาพเพื่อบันทึกงาน")

        return DailySummaryReport(
            report_date=target_date,
            total_users=len(users_map),
            total_tasks=total_tasks,
            completed_count=completed_count,
            in_progress_count=in_progress_count,
            blocker_count=blocker_count,
            user_summaries=user_summaries,
            formatted_line_message="\n".join(msg_lines).strip()
        )

    @staticmethod
    def generate_morning_briefing(items: List[WorkItem], target_date: date = None) -> str:
        if target_date is None:
            target_date = date.today()

        if not items:
            return (
                f"☀️ อรุณสวัสดิ์ครับ! แจ้งตารางภารกิจประจำวัน ({target_date.strftime('%d/%m/%Y')})\n"
                f"สำนักงานพาณิชย์จังหวัดเพชรบุรี\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ วันนี้ยังไม่มีกำหนดการหรือตารางงานที่บันทึกไว้\n\n"
                f"💪 ขอให้เป็นวันที่ราบรื่นและมีความสุขกับการทำงานครับ!"
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
            f"☀️ อรุณสวัสดิ์ครับ! ตารางภารกิจประจำวันนี้ ({target_date.strftime('%d/%m/%Y')})",
            f"สำนักงานพาณิชย์จังหวัดเพชรบุรี (แจ้งเตือน 07:30 น.)",
            f"━━━━━━━━━━━━━━━━━━",
            f"📋 รายการภารกิจและตารางงานวันนี้ ({len(unique_items)} รายการ):",
            ""
        ]

        for idx, item in enumerate(unique_items[:30], 1):
            time_tag = f"[{item.scheduled_time}] " if item.scheduled_time else ""
            user_tag = f" ({item.user_name})" if item.user_name and item.user_name != "Anonymous" else ""
            lines.append(f"{idx}. 📌 {time_tag}{item.task_text}{user_tag}")

        if len(unique_items) > 30:
            lines.append(f"\n... และมีรายการอื่นๆ อีก {len(unique_items) - 30} รายการ")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("💪 ขอให้ทุกคนทำงานอย่างราบรื่นและมีพลังตลอดทั้งวันครับ!")

        return "\n".join(lines).strip()
