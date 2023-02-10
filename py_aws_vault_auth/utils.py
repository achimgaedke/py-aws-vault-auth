import threading

NL_CHARS_LIST = [b"\r\n", b"\n"]
CHAR_CODE = "utf-8"


class non_block_read(threading.Thread):

    def __init__(self, stream):
        threading.Thread.__init__(self)
        self.stream = stream
        self.buffer_lock = threading.Lock()
        self.read_buffer = b""

    def get_text(self):
        with self.buffer_lock:
            buffer, self.read_buffer = self.read_buffer, b""
        return buffer.decode(encoding=CHAR_CODE)

    def get_completed_lines(self):
        buffer = b""
        with self.buffer_lock:
            for nl_chars in NL_CHARS_LIST:
                last_complete = self.read_buffer.rfind(nl_chars)
                if last_complete != -1:
                    last_complete += len(nl_chars)
                    buffer, self.read_buffer = (
                        self.read_buffer[:last_complete],
                        self.read_buffer[last_complete:])
                    break
        return buffer.decode(encoding=CHAR_CODE)

    def run(self):
        next_char = self.stream.read(1)
        while next_char:
            with self.buffer_lock:
                self.read_buffer += next_char
            next_char = self.stream.read(1)
