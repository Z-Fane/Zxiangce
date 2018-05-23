from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

from app import User


class LoginForm(Form):
    email = StringField(u'邮箱', validators=[DataRequired(message=u'邮箱不能为空'), Length(1, 64),
                                           Email(message=u'请输入有效的邮箱地址，比如：username@domain.com')])
    password = PasswordField(u'密码', validators=[DataRequired(message=u'密码不能为空')])
    submit = SubmitField(u'登录')


class RegisterForm(Form):
    username = StringField(u'用户名', validators=[DataRequired(message=u'用户名不能为空'), Length(1, 64)])
    email = StringField(u'邮箱', validators=[DataRequired(message=u'邮箱不能为空'), Length(1, 64),
                                           Email(message=u'请输入有效的邮箱地址，比如：username@domain.com')])
    password = PasswordField(u'密码', validators=[DataRequired(message=u'密码不能为空'),
                                                EqualTo('password2', message=u'密码必须相等')])
    password2 = PasswordField(u'确认密码', validators=[DataRequired(message=u'密码不能为空')])
    submit = SubmitField(u'注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已经注册，请直接登录。')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError(u'用户名已被注册，换一个吧。')


class PasswordResetRequestForm(Form):
    email = StringField(u'邮箱', validators=[DataRequired(message=u'邮箱不能为空'), Length(1, 64),
                                           Email(message=u'请输入有效的邮箱地址，比如：username@domain.com')])
    submit = SubmitField(u'重设密码')


class ChangePasswordForm(Form):
    old_password = PasswordField(u'旧密码', validators=[DataRequired(message=u'密码不能为空')])
    password = PasswordField(u'新密码', validators=[
        DataRequired(message=u'密码不能为空'), EqualTo('password2', message=u'密码必须匹配。')])
    password2 = PasswordField(u'确认新密码', validators=[DataRequired(message=u'密码不能为空')])
    submit = SubmitField(u'更改')


class ChangeEmailForm(Form):
    email = StringField(u'新邮箱地址', validators=[DataRequired(message=u'邮箱不能为空'), Length(1, 64),
                                              Email(message=u'请输入有效的邮箱地址，比如：username@domain.com')])
    password = PasswordField(u'密码', validators=[DataRequired(message=u'密码不能为空')])
    submit = SubmitField(u'更新')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已经注册过了，换一个吧。')


class PasswordResetForm(Form):
    password = PasswordField(u'新密码', validators=[
        DataRequired(message=u'密码不能为空')])
    submit = SubmitField(u'重设')
