from wtforms import (
    Form,
    BooleanField,
    StringField,
    PasswordField,
    EmailField, 
    SelectField,
    FileField,
    validators,
    ValidationError
)

from models import PostType

def validate_image_extension(filename):
    return filename.endswith((".jpg", ".jpeg", ".png"))

def image_extension(form, field):
    if field.data and field.data.filename != "" and not validate_image_extension(field.data.filename):
        raise ValidationError("Допускаются изображения в форматах: .jpg, .png")

def image_extension_requred(form, field):
    if field.data and not validate_image_extension(field.data.filename):
        raise ValidationError("Допускаются изображения в форматах: .jpg, .png")
    

def bin_extension(form, field):
    if field.data and not field.data.filename.endswith(".bin"):
        raise ValidationError("Ожидается формат .bin")


class LoginForm(Form):
    username = StringField('Имя пользователя', [
        validators.DataRequired(message="Заполните данное поле")
    ], default="", description="Ваш ник")
    password = PasswordField('Пароль', [
        validators.DataRequired(message="Заполните данное поле")
    ], description="Пароль от 8 символов")

class RegisterForm(Form):
    username = StringField('Имя пользователя', [
        validators.DataRequired(message="Заполните данное поле"),
        validators.Length(min=1, max=32, message="Имя пользователя должно содержать от 1 до 32 символов")
    ], default="", description="Ваш ник")
    email = EmailField("Почта", [
        validators.DataRequired(message="Заполните данное поле"),
        validators.Email("Неверно указан формат почты")
    ], default="", description="user@mail.com")
    password = PasswordField('Пароль', [
        validators.DataRequired(message="Заполните данное поле"),
        validators.Length(min=8, max=64, message="Длина пароля должна быть от 8 до 64 символов")
    ], description="Пароль")
    password_confirm = PasswordField('Подтверждение пароля', [
        validators.DataRequired(message="Заполните данное поле"),
        validators.EqualTo("password", "Пароли не совпадают")
    ], description="Повторите пароль")

class ChangeEnableNotificationsForm(Form):
    enable_notifications = BooleanField("Разрешить оповещения по почте", [
    ],default=True, description="Включите или отключите оповещения")

class GenResetPasswordForm(Form):
    username = StringField('Имя пользователя', [
        validators.DataRequired(message="Заполните данное поле"),
        validators.Length(min=1, max=32, message="Имя пользователя должно содержать от 1 до 32 символов")
    ], default="", description="Ваш ник")
    email = EmailField("Почта", [
        validators.DataRequired(message="Заполните данное поле"),
        validators.Email("Неверно указан формат почты")
    ], default="", description="user@mail.com")

class ResetPasswordForm(Form):
    password = PasswordField('Пароль', [
        validators.DataRequired(message="Заполните данное поле"),
        validators.Length(min=8, max=64, message="Длина пароля должна быть от 8 до 64 символов")
    ], description="Пароль")
    password_confirm = PasswordField('Подтверждение пароля', [
        validators.DataRequired(message="Заполните данное поле"),
        validators.EqualTo("password", "Пароли не совпадают")
    ], description="Повторите пароль")

class PostForm(Form):
    title = StringField("Название", [
        validators.DataRequired(message="Заполните данное поле")
    ], default="", description="Введите заголовок")
    type = SelectField("Тип", [
        validators.DataRequired(message="Заполните данное поле")
    ], choices=[(t.name, t.value) for t in PostType])
    summary = StringField("Краткое описание, до 1000 символов", [
        validators.DataRequired(message="Заполните данное поле"),
        validators.Length(max=1000, message="До 1000 символов")
    ], default="", description="Краткое описание, до 1000 символов")
    preview = FileField("Превью", [image_extension])
    content = StringField("Содержание", [
        validators.DataRequired(message="Заполните данное поле"),
    ], default="", description="Содержание в формате markdown")

class GameForm(Form):
    title = StringField("Название игры", [
        validators.DataRequired(message="Заполните данное поле")
    ], default="", description="Введите название")
    description = StringField("Описание", [
        validators.DataRequired(message="Заполните данное поле"),
    ], default="", description="Описание игры в формате markdown")
    preview = FileField("Превью", [image_extension_requred])
    binary = FileField("Файл игры", [bin_extension])
