import logging

# 모듈 레벨 로거 (부모에서 주입 가능). 기본은 NullHandler로 안전하게 무시
logger: logging.Logger = logging.getLogger("wf_gen_code")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def set_logger(external_logger: logging.Logger):
    global logger
    logger = external_logger


import random
from collections import Counter


def generate_code_with_limited_duplicates(k: int = 6) -> str:
    """랜덤 숫자 코드 생성 (중복 제한 규칙 적용)

    규칙:
    - 자릿수(k)와 무관하게 같은 숫자는 최대 2번까지만 허용 (count <= 2)
    - 두 번 등장하는 숫자는 전체에서 최대 1종류만 허용 (pair 개수 <= 1)

    예:
    - 허용: 193524 (모두 고유), 193534 (3이 한 번만 중복), 113524 (1이 한 번만 중복)
    - 불허: 113534 (1과 3이 각각 2회씩 → pair 2개)
    """
    digits = "0123456789"
    while True:
        code = "".join(random.choices(digits, k=k))
        cnt = Counter(code)
        if all(v <= 2 for v in cnt.values()) and sum(1 for v in cnt.values() if v == 2) <= 1:
            return code


# 예시 10개 생성
def test_generate_code():
    for _ in range(10):
        code = generate_code_with_limited_duplicates()
        cnt = Counter(code)
        pair_count = sum(1 for v in cnt.values() if v == 2)
        assert all(v <= 2 for v in cnt.values()) and pair_count <= 1, f"규칙 위반: {code} {cnt}"
        logger.info(code)


if __name__ == "__main__":
    try:
        from wf_log import get_app_logger

        set_logger(get_app_logger("wf_gen_code", console_level=logging.INFO))
    except Exception:
        pass
    test_generate_code()
