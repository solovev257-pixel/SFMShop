class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
    
    def get_info(self):
        return "Пользователь: " + self.name + ", Email: " + self.email

def validate_email(self):
    if "@" not in self.email:
        raise ValueError("Неверный формат email")
    return True