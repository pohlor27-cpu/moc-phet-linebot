import logging
from typing import Optional, List

logger = logging.getLogger("LineClient")

def split_message_chunks(text: str, max_chunk_size: int = 4000, max_messages: int = 5) -> List[str]:
    """Splits a long text into chunks that satisfy LINE message length constraints (<= 5000 chars each, max 5 per reply)."""
    if not text or not text.strip():
        return ["(ไม่มีข้อความ)"]
    
    text = text.strip()
    if len(text) <= max_chunk_size:
        return [text]

    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_chunk_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            while len(line) > max_chunk_size:
                chunks.append(line[:max_chunk_size])
                line = line[max_chunk_size:]
        current_chunk.append(line)
        current_len += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks[:max_messages]

class LineBotClient:
    def __init__(self, channel_access_token: str, channel_secret: str):
        self.channel_access_token = channel_access_token
        self.channel_secret = channel_secret
        self.sent_messages: List[dict] = []  # For testing & audit
        self._init_client()

    def _init_client(self):
        try:
            from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, MessagingApiBlob
            configuration = Configuration(access_token=self.channel_access_token)
            self.api_client = ApiClient(configuration)
            self.messaging_api = MessagingApi(self.api_client)
            self.messaging_api_blob = MessagingApiBlob(self.api_client)
            self.is_configured = bool(self.channel_access_token and self.channel_access_token != "dummy_channel_access_token")
        except Exception as e:
            logger.warning(f"Line SDK init warning (running in standalone/mock mode): {e}")
            self.is_configured = False

    def reply_text(self, reply_token: str, text: str):
        self.sent_messages.append({"action": "reply", "reply_token": reply_token, "text": text})
        if not self.is_configured:
            logger.info(f"[MOCK LINE REPLY] Token={reply_token}: {text[:100]}...")
            return

        try:
            from linebot.v3.messaging import ReplyMessageRequest, TextMessage
            chunks = split_message_chunks(text)
            messages = [TextMessage(text=c) for c in chunks]
            request = ReplyMessageRequest(
                reply_token=reply_token,
                messages=messages
            )
            self.messaging_api.reply_message(request)
            logger.info(f"Successfully sent LINE reply with {len(messages)} message chunk(s)")
        except Exception as e:
            logger.error(f"Error sending Line reply: {e}")

    def broadcast_summary(self, text: str):
        self.sent_messages.append({"action": "broadcast", "text": text})
        if not self.is_configured:
            logger.info(f"[MOCK LINE BROADCAST]: {text[:100]}...")
            return

        try:
            from linebot.v3.messaging import BroadcastRequest, TextMessage
            chunks = split_message_chunks(text)
            messages = [TextMessage(text=c) for c in chunks]
            request = BroadcastRequest(messages=messages)
            self.messaging_api.broadcast(request)
            logger.info(f"Successfully broadcasted {len(messages)} message chunk(s)")
        except Exception as e:
            logger.error(f"Error broadcasting Line message: {e}")

    def get_message_content(self, message_id: str) -> bytes:
        if not self.is_configured:
            return b"1. [Done] Finished testing OCR\n2. [In Progress] Deploying to server"

        try:
            content = self.messaging_api_blob.get_message_content(message_id)
            if isinstance(content, (bytearray, bytes)):
                return bytes(content)
            elif hasattr(content, "raw_data"):
                return bytes(content.raw_data)
            return bytes(content)
        except Exception as e:
            logger.error(f"Error fetching message content {message_id}: {e}")
            return b""

    def get_user_display_name(self, user_id: str, group_id: Optional[str] = None) -> str:
        if not self.is_configured or not user_id or user_id == "unknown_user":
            return "ผู้ใช้"

        try:
            if group_id:
                profile = self.messaging_api.get_group_member_profile(group_id=group_id, user_id=user_id)
                return profile.display_name
            else:
                profile = self.messaging_api.get_profile(user_id=user_id)
                return profile.display_name
        except Exception:
            return "ผู้ใช้"
