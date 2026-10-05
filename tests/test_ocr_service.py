import pytest
from domain.models import TaskStatus
from services.ocr_service import OCRService

def test_parse_text_to_work_items():
    service = OCRService(provider="mock")
    text = (
        "1. [เสร็จแล้ว] แก้ไขบั๊กหน้า Login\n"
        "2. [กำลังทำ] เขียน Test Suite\n"
        "3. [ติดปัญหา] รอ API Token จากระบบกลาง"
    )
    items = service.parse_text_to_work_items(text, user_id="U100", user_name="Somchai")
    assert len(items) == 3
    
    assert items[0].task_text == "แก้ไขบั๊กหน้า Login"
    assert items[0].status == TaskStatus.DONE
    
    assert items[1].task_text == "เขียน Test Suite"
    assert items[1].status == TaskStatus.IN_PROGRESS
    
    assert items[2].task_text == "รอ API Token จากระบบกลาง"
    assert items[2].status == TaskStatus.BLOCKER

def test_ocr_process_mock_image():
    service = OCRService(provider="mock")
    dummy_image = b"1. [Done] Built FastAPI bot\n2. [In Progress] Verify with pytest"
    result = service.process_image(dummy_image, user_id="U200", user_name="Alice")
    
    assert result.confidence > 0.0
    assert len(result.detected_tasks) == 2
    assert result.detected_tasks[0].status == TaskStatus.DONE
    assert result.detected_tasks[1].status == TaskStatus.IN_PROGRESS
