from datetime import date, timedelta
from typing import List, Dict, Optional
from domain.models import WorkItem, TaskStatus, DailySummaryReport, UserDailySummary

class DailySummarizer:
    @staticmethod
    def generate_daily_report(items: List[WorkItem], target_date: Optional[date] = None) -> DailySummaryReport:
        if target_date is None:
            target_date = date.today()

        today = date.today()
        date_label = "วันนี้" if target_date == today else ("เมื่อวาน" if target_date == today - timedelta(days=1) else target_date.strftime('%d/%m/%Y'))

        if not items:
            formatted_msg = (
                f"📊 สรุปรายงานประจำ{date_label} ({target_date.strftime('%d/%m/%Y')})\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"❌ ยังไม่มีการบันทึกรายการงานสำหรับ{date_label}\n\n"
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
            f"📊 สรุปงานประจำ{date_label} ({target_date.strftime('%d/%m/%Y')})",
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
        msg_lines.append("🚀 พิมพ์ 'ตารางงาน' เพื่อดูภารกิจ หรือส่งข้อความ/รูปภาพเพื่อบันทึกงาน")

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
    def generate_morning_briefing(items: List[WorkItem], target_date: Optional[date] = None) -> str:
        if target_date is None:
            target_date = date.today()

        today = date.today()
        if target_date == today:
            title_prefix = "☀️ อรุณสวัสดิ์ครับ! ตารางภารกิจประจำวันนี้"
            empty_prefix = "✨ วันนี้ยังไม่มีกำหนดการหรือตารางงานที่บันทึกไว้"
        elif target_date == today + timedelta(days=1):
            title_prefix = "📅 ตารางภารกิจประจำวันพรุ่งนี้"
            empty_prefix = "✨ วันพรุ่งนี้ยังไม่มีกำหนดการหรือตารางงานที่บันทึกไว้"
        else:
            title_prefix = f"📅 ตารางภารกิจประจำวันที่ {target_date.strftime('%d/%m/%Y')}"
            empty_prefix = f"✨ วันที่ {target_date.strftime('%d/%m/%Y')} ยังไม่มีกำหนดการที่บันทึกไว้"

        if not items:
            return (
                f"{title_prefix} ({target_date.strftime('%d/%m/%Y')})\n"
                f"สำนักงานพาณิชย์จังหวัดเพชรบุรี\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{empty_prefix}\n\n"
                f"💡 คุณสามารถส่งรูปภาพตารางงานหรือพิมพ์ระบุเพื่อบันทึกงานล่วงหน้าได้ครับ!"
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
            f"📋 รายการภารกิจและตารางงาน ({len(unique_items)} รายการ):",
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
