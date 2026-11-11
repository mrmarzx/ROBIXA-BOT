import random
import string


def generate_username() -> str:
    """HHabVI + 11 random alphanumeric chars"""
    prefix = "HHabVI"
    chars = string.ascii_letters + string.digits
    return prefix + "".join(random.choices(chars, k=11))


def generate_password() -> str:
    """PASS--HH----#D--- with random chars replacing dashes"""
    template = list("PASS--HH----#D---")
    chars = string.ascii_letters + string.digits
    for i, c in enumerate(template):
        if c == "-":
            template[i] = random.choice(chars)
    return "".join(template)


def generate_test_username() -> str:
    chars = string.ascii_lowercase + string.digits
    return "TEST" + "".join(random.choices(chars, k=8))
