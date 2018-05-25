from flask import Blueprint, flash, redirect, request, url_for, render_template, current_app, jsonify
from flask_login import login_user, login_required, logout_user, current_user

from app import User, db
from app.auth.forms import LoginForm, RegisterForm, PasswordResetRequestForm, ChangePasswordForm, ChangeEmailForm, \
    PasswordResetForm
from app.tasks import send_email, long_task
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


auth = Blueprint('auth', __name__, url_prefix='/auth')


@auth.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, True)
            flash(u'登陆成功。', 'info')
            return redirect(request.args.get('next') or url_for('main.index'))
        flash(u'用户名或密码无效，请检查。', 'warning')
    return render_template('auth/login.html', form=form)


@auth.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data,
                    email=form.email.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, u'确认你的账户',
                   'email/confirm', user=user, token=token)

        flash(u'确认邮件已经发送到您的邮箱，请查收。', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)



@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash(u'你的账户已经确认，欢迎！', 'info')
    else:
        flash(u'抱歉，验证链接无效或已经过期。', 'warning')
    return redirect(url_for('main.index'))


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, u'重设密码',
                       'email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash(u'密码重设邮件已经发送到你的邮箱，请及时查收。', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', form=form)



@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    #判断token
    s=Serializer(current_app.config['SECRET_KEY'])
    try:
        data=s.loads(token)
    except:
        return redirect('main.index')
    user_id=data.get('reset_password')
    if user_id==None:
        return redirect('main.index')
    user = User.query.filter_by(id=user_id).first()
    if user==None:
        return redirect('main.index')
    form=PasswordResetForm()
    if form.validate_on_submit():
        user.password=form.password.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html',form=form,token=token)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form=ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash(u'你的密码已经更新。', 'success')
            return redirect(url_for('.logout'))
        else:
            flash(u'密码无效。', 'warning')
    return render_template("auth/change_password.html", form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, u'确认你的邮箱地址',
                       'email/change_email',
                       user=current_user, token=token)
            flash(u'一封确认邮件已经发送到你的新邮箱，请及时查收。', 'info')
            return redirect(url_for('main.index'))
        else:
            flash(u'邮箱地址或密码无效。', 'warning')
    return render_template("auth/change_email.html", form=form)



@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash(u'你的邮箱地址已经更新。', 'success')
    else:
        flash(u'请求无效.', 'warning')
    return redirect(url_for('main.index'))


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash(u'你已经注销。', 'info')
    return redirect(url_for('main.index'))

@auth.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
            and request.endpoint[:5] != 'auth.':
            return redirect(url_for('auth.unconfirmed'))

@auth.before_app_request
def before_request():
    if current_user.is_authenticated \
        and not current_user.confirmed \
        and request.endpoint[:5] != 'auth.' \
        and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')



@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, u'确认你的账户',
               'email/confirm', user=current_user, token=token)
    flash(u'新的确认邮件已经发送到您的邮箱，请查收。', 'info')
    return redirect(url_for('main.index'))

@auth.route('/longtask')
def longtask():
    task=long_task.apply_async()
    return jsonify({}), 202, {'Location': url_for('.taskstatus', task_id=task.id)}

@auth.route('/status/<task_id>')
def taskstatus(task_id):
    # 获取异步任务结果
    task = long_task.AsyncResult(task_id)
    # 等待处理
    if task.state == 'PENDING':
        response = {'state': task.state, 'current': 0, 'total': 1}
    elif task.state != 'FAILURE':
        response = {'state': task.state, 'current': task.info.get('current', 0), 'total': task.info.get('total', 1)}
        # 处理完成
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # 后台任务出错
        response = {'state': task.state, 'current': 1, 'total': 1}
    return jsonify(response)



