from flask_wtf import Form
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, FileField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from app import photos


class NewAlbumForm(Form):
    title = StringField(u'标题')
    about = TextAreaField(u'介绍', render_kw={'rows': 8})
    photo = FileField(u'图片', validators=[
        FileRequired(u'你还没有选择图片！'),
        FileAllowed(photos, u'只能上传图片！')
    ])
    asc_order = SelectField(u'显示顺序',
                            choices=[('True', u'按上传时间倒序排列'), ('False', u'按上传时间倒序排列')])
    no_public = BooleanField(u'私密相册（勾选后相册仅自己可见）')
    no_comment = BooleanField(u'禁止评论')
    submit = SubmitField(u'提交')

    def create_album(self):
        pass

class CommentForm(Form):
    body = TextAreaField(u'留言', validators=[DataRequired(u'内容不能为空！')], render_kw={'rows': 5})
    submit = SubmitField(u'提交')

class EditAlbumForm(Form):
    title = StringField(u'标题')
    about = TextAreaField(u'介绍', render_kw={'rows': 8})
    asc_order = SelectField(u'显示顺序',
                             choices=[("1", u'按上传时间倒序排列'), ("0", u'按上传时间倒序排列')])
    no_public = BooleanField(u'私密相册（右侧滑出信息提示：勾选后相册仅自己可见）')
    no_comment = BooleanField(u'允许评论')
    submit = SubmitField(u'提交')
class AddPhotoForm(Form):
    photo = FileField(u'图片', validators=[
        FileRequired(),
        FileAllowed(photos, u'只能上传图片！')
    ])
    submit = SubmitField(u'提交')
class SettingForm(Form):
    username = StringField(u'姓名或昵称', validators=[Length(0, 64)])
    status = StringField(u'签名档', validators=[Length(0, 64)])
    location = StringField(u'城市', validators=[Length(0, 64)])
    website = StringField(u'网站', validators=[Length(0, 64), Optional(),
                         ], render_kw={"placeholder": "http://..."})
    about_me = TextAreaField(u'关于我', render_kw={'rows': 8})
    like_public = BooleanField(u'公开我的喜欢')
    submit = SubmitField(u'提交')

    def validate_website(self, field):
        if field.data[:4] != "http":
             field.data = "http://" + field.data
