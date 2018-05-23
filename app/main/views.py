import hashlib
import os
import time

import PIL
import bleach
from PIL import Image
from flask import Blueprint, flash, redirect, url_for, render_template, request, current_app, abort, send_from_directory
from flask_login import login_required, current_user

from app import User, db, photos
from app.main.forms import NewAlbumForm, CommentForm, EditAlbumForm, AddPhotoForm, SettingForm
from app.model import Photo, Album, Message, Comment

main = Blueprint('main', __name__, url_prefix='/')

# 首页
@main.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        photos = current_user.photos_like.all()
        photos = [photo for photo in photos if photo.album.no_public == False]
    else:
        photos = ""
    return render_template('index.html', photos=photos)

# # 关于
# @main.route('/about')
# def about():
#     return render_template('about.html')

# 关注用户
@main.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('.albums', username=username))

# 取关
@main.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('.albums', username=username))


# 用户喜欢的照片
@main.route('/<username>/likes')
def likes(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    if current_user != user and not user.like_public:
        return render_template('like_no_public.html', user=user)
    page = request.args.get('page', 1, type=int)
    pagination = user.photo_likes.paginate(
        page, per_page=current_app.config['ZXIANGCE_PHOTO_LIKES_PER_PAGE'], error_out=False)
    photo_likes = pagination.items
    photo_likes = [{'photo': photo, 'timestamp': photo.timestamp, 'url_t': photo.url_t} for photo in
                   photo_likes]
    type = "photo"
    return render_template('likes.html', user=user, photo_likes=photo_likes,
                           pagination=pagination, type=type)

# 探索，
@main.route('/explore', methods=['GET', 'POST'])
def explore():
    photos = Photo.query.order_by(Photo.timestamp.desc()).all()
    photos = [photo for photo in photos if photo.album.no_public == False and photo.author != current_user]
    photo_type = "new"
    return render_template('explore.html', photos=photos, type=photo_type)
    pass

# 探索_热门
@main.route('/explore/hot', methods=['GET', 'POST'])
def explore_hot():
    photos = Photo.query.all()
    photos = [photo for photo in photos if photo.album.no_public == False]
    result = {}
    for photo in photos:
        result[photo] = len(list(photo.user_like))
    sorted_photo = sorted(result.items(), key=lambda x: x[1], reverse=True)
    temp = []
    for photo in sorted_photo:
        temp.append(photo[0])
    photo_type = "hot"
    return render_template('explore.html', photos=temp, type=photo_type)

# 保存图片
def save_image(files):
    photo_amount = len(files)
    if photo_amount > 50:
        flash(u'抱歉，测试阶段每次上传不超过50张！', 'warning')
        return redirect(url_for('.new_album'))
    images = []
    for img in files:
        filename = hashlib.md5((current_user.username + str(time.time())).encode('utf8')).hexdigest()[:10]
        image = photos.save(img, name=filename + '.')
        file_url = photos.url(image)
        url_s = image_resize(image, 800)
        url_t = image_resize(image, 300)
        images.append((file_url, url_s, url_t))
    return images

# 新建相册
@main.route('/new-album', methods=['GET', 'POST'])
@login_required
def new_album():
    form = NewAlbumForm()
    if form.validate_on_submit(): # current_user.can(Permission.CREATE_ALBUMS)
        if request.method == 'POST' and 'photo' in request.files:
            images = save_image(request.files.getlist('photo'))
        title = form.title.data
        about = form.about.data
        author = current_user._get_current_object()
        no_public = form.no_public.data
        no_comment = form.no_comment.data
        album = Album(title=title, about=about,
                      cover=images[0][2], author=author,
                      no_public=no_public, no_comment=no_comment)
        db.session.add(album)

        for url in images:
            photo = Photo(url=url[0], url_s=url[1], url_t=url[2],
                          album=album, author=current_user._get_current_object())
            db.session.add(photo)
        db.session.commit()
        flash(u'相册创建成功！', 'success')
        return redirect(url_for('.edit_photo', id=album.id))

    return render_template('new_album.html', form=form)


img_suffix = {
    300: '_t',  # thumbnail
    800: '_s'  # show
}


def image_resize(image, base_width):
    #: create thumbnail
    filename, ext = os.path.splitext(image)
    img = Image.open(photos.path(image))
    if img.size[0] <= base_width:
        return photos.url(image)
    w_percent = (base_width / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
    img.save(os.path.join(current_app.config['UPLOADED_PHOTO_DEST'], filename + img_suffix[base_width] + ext))
    return url_for('.uploaded_file', filename=filename + img_suffix[base_width] + ext)
# 上传图片
@main.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOADED_PHOTO_DEST'],
                               filename)
# 上传页面
@main.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    return render_template('upload.html')

# 添加到相册里
@main.route('/upload-add', methods=['GET', 'POST'])
@login_required
def upload_add():
    id = request.form.get('album')
    return redirect(url_for('.add_photo', id=id))

# 添加照片
@main.route('/add-photo/<int:id>', methods=['GET', 'POST'])
@login_required
def add_photo(id):
    album = Album.query.get_or_404(id)
    form = AddPhotoForm()
    if form.validate_on_submit():  # current_user.can(Permission.CREATE_ALBUMS)
        if request.method == 'POST' and 'photo' in request.files:
            images = save_image(request.files.getlist('photo'))

            for url in images:
                photo = Photo(url=url[0], url_s=url[1], url_t=url[2],
                              album=album, author=current_user._get_current_object())
                db.session.add(photo)
            db.session.commit()
        flash(u'图片添加成功！', 'success')
        return redirect(url_for('.album', id=album.id))
    return render_template('add_photo.html', form=form, album=album)

# 编辑用户个人信息
@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    return redirect(url_for('.setting') + '#profile')


# 编辑照片信息
@main.route('/edit-photo/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_photo(id):
    album = Album.query.get_or_404(id)
    photos = album.photos.order_by(Photo.order.asc())
    if request.method == 'POST':
        for photo in photos:
            photo.about = request.form[str(photo.id)]
            photo.order = request.form["order-" + str(photo.id)]
            db.session.add(photo)
        album.cover = request.form['cover']
        db.session.add(album)
        db.session.commit()
        flash(u'更改已保存。', 'success')
        return redirect(url_for('.album', id=id))
    enu_photos = []
    for index, photo in enumerate(photos):
        enu_photos.append((index, photo))

    return render_template('edit_photo.html', album=album, photos=photos, enu_photos=enu_photos)

# 用户所有相册
@main.route('/<username>', methods=['GET', 'POST'])
def albums(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    page = request.args.get('page', 1, type=int)
    pagination = user.albums.order_by(Album.timestamp.desc()).paginate(
            page, per_page=current_app.config['ZXIANGCE_ALBUMS_PER_PAGE'], error_out=False)
    albums = pagination.items

    photo_count = sum([len(album.photos.all()) for album in albums])
    album_count = len(albums)

    allowed_tags = ['br']
    if user.about_me:
        about_me = bleach.linkify(bleach.clean(
            user.about_me.replace('\r', '<br>'), tags=allowed_tags, strip=True))
    else:
        about_me = None
    form = CommentForm()
    if form.validate_on_submit() and current_user.is_authenticated:
        comment = Message(body=form.body.data,
                          user=user,
                          author=current_user._get_current_object())
        db.session.add(comment)
        flash(u'你的评论已经发表。', 'success')
        return redirect(url_for('.albums', username=username))

    return render_template('albums.html', form=form,
                           user=user, albums=albums, album_count=album_count,
                           photo_count=photo_count, pagination=pagination,
                           about_me=about_me)

# 查看指定相册
@main.route('/album/<int:id>')
def album(id):
    album = Album.query.get_or_404(id)
    # display default cover when an album is empty
    placeholder = 'http://p1.bpimg.com/567591/15110c0119201359.png'
    photo_amount = len(list(album.photos))
    if photo_amount == 0:
        album.cover = placeholder
    elif photo_amount != 0 and album.cover == placeholder:
        album.cover = album.photos[0].url
    if current_user != album.author and album.no_public == True:
        abort(404)
    page = request.args.get('page', 1, type=int)
    if album.asc_order:
        pagination = album.photos.order_by(Photo.order.asc()).paginate(
            page, per_page=current_app.config['ZXIANGCE_PHOTOS_PER_PAGE'],
            error_out=False)
    else:
        pagination = album.photos.order_by(Photo.order.asc()).paginate(
            page, per_page=current_app.config['ZXIANGCE_PHOTOS_PER_PAGE'],
            error_out=False)
    photos = pagination.items
    if len(photos) == 0:
        no_pic = True
    else:
        no_pic = False


    return render_template('album.html', album=album, photos=photos, pagination=pagination,
                            no_pic=no_pic)

# 查看指定照片
@main.route('/photo/<int:id>', methods=['GET', 'POST'])
def photo(id):
    photo = Photo.query.get_or_404(id)
    album = photo.album
    if current_user != album.author and album.no_public == True:
        abort(404)

    photo_sum = len(list(album.photos))
    form = CommentForm()
    photo_index = [p.id for p in album.photos.order_by(Photo.order.asc())].index(photo.id) + 1
    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = Comment(body=form.body.data,
                              photo=photo,
                              author=current_user._get_current_object())
            db.session.add(comment)
            flash(u'你的评论已经发表。', 'success')
            return redirect(url_for('.photo', id=photo.id))
        else:
            flash(u'请先登录。', 'info')
    page = request.args.get('page', 1, type=int)
    pagination = photo.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['ZXIANGCE_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    amount = len(comments)
    return render_template('photo.html', form=form, album=album, amount=amount,
                           photo=photo, pagination=pagination,
                           comments=comments, photo_index=photo_index, photo_sum=photo_sum)

# 下一张
@main.route('/photo/n/<int:id>')
def photo_next(id):
    "redirect to next imgae"
    photo_now = Photo.query.get_or_404(id)
    album = photo_now.album
    photos = album.photos.order_by(Photo.order.asc())
    position = list(photos).index(photo_now) + 1
    if position == len(list(photos)):
        flash(u'已经是最后一张了。', 'info')
        return redirect(url_for('.photo', id=id))
    photo = photos[position]
    return redirect(url_for('.photo', id=photo.id))

# 上一张
@main.route('/photo/p/<int:id>')
def photo_previous(id):
    "redirect to previous imgae"
    photo_now = Photo.query.get_or_404(id)
    album = photo_now.album
    photos = album.photos.order_by(Photo.order.asc())
    position = list(photos).index(photo_now) - 1
    if position == -1:
        flash(u'已经是第一张了。', 'info')
        return redirect(url_for('.photo', id=id))
    photo = photos[position]
    return redirect(url_for('.photo', id=photo.id))

# 保存图片后编辑照片信息
@main.route('/save-photo-edit/<int:id>', methods=['GET', 'POST'])
@login_required
def save_photo_edit(id):
    photo = Photo.query.get_or_404(id)
    album = photo.album
    photo.about = request.form.get('about', '')
    # set default_value to avoid 400 error.
    default_value = album.cover
    print (default_value)
    album.cover = request.form.get('cover', default_value)
    db.session.add(photo)
    db.session.add(album)
    db.session.commit()
    flash(u'更改已保存。', 'success')
    return redirect(url_for('.photo', id=id))

# 喜欢某个照片
@main.route('/photo/like/<id>')
@login_required
#@permission_required(Permission.FOLLOW)
def like_photo(id):
    photo = Photo.query.filter_by(id=id).first()
    album = photo.album
    if photo is None:
        flash(u'无效的图片。', 'warning')
        return redirect(url_for('.album', id=album))
    if current_user.is_like_photo(photo):
        current_user.unlike_photo(photo)
        redirect(url_for('.photo', id=id))
    else:
        current_user.like_photo(photo)

    return redirect(url_for('.photo', id=id))


# 喜欢某个相册
@main.route('/album/like/<id>')
@login_required
def like_album(id):
    album = Album.query.filter_by(id=id).first()
    if album is None:
        flash(u'无效的相册。', 'warning')
        return redirect(url_for('.albums', username=album.author.username))
    if current_user.is_like_album(album):
        current_user.unlike_album(album)
        flash(u'喜欢已取消。', 'info')
        redirect(url_for('.album', id=id))
    else:
        current_user.like_album(album)
        flash(u'相册已经添加到你的喜欢里了。', 'success')
    return redirect(url_for('.album', id=id))

# 我关注的用户
@main.route('/followeds/<username>')
def followeds(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'操作无效。', 'warning')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['ZXIANGCE_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item, 'timestamp': item.member_since}
               for item in pagination.items]
    return render_template('followers.html', user=user, title=u"关注的人",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)

# 粉丝列表
@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'操作无效。', 'warning')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=10, #current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item, 'timestamp': item.member_since}
               for item in pagination.items]
    return render_template('followers.html', user=user, title=u"的粉丝",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)
# 编辑相册
@main.route('/edit-album/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_album(id):
    album = Album.query.get_or_404(id)
    form = EditAlbumForm()
    if form.validate_on_submit():
        album.title = form.title.data
        album.about = form.about.data
        album.asc_order = form.asc_order.data
        album.no_public = form.no_public.data
        album.no_comment = form.no_comment.data
        album.author = current_user._get_current_object()
        flash(u'更改已保存。', 'success')
        return redirect(url_for('.album', id=id))
    form.title.data = album.title
    form.about.data = album.about
    form.asc_order.data = album.asc_order
    form.no_comment.data = album.no_comment
    form.no_public.data = album.no_public
    return render_template('edit_album.html', form=form, album=album)

# 整理相册
@main.route('/fast-sort/<int:id>', methods=['GET', 'POST'])
@login_required
def fast_sort(id):
    album = Album.query.get_or_404(id)
    photos = album.photos.order_by(Photo.order.asc())
    enu_photos = []
    for index, photo in enumerate(photos):
        enu_photos.append((index, photo))
    return render_template('fast_sort.html', album=album, photos=photos, enu_photos=enu_photos)

@main.route('/save-sort/<int:id>', methods=['GET', 'POST'])
@login_required
def save_sort(id):
    album = Album.query.get_or_404(id)
    photos = album.photos
    for photo in photos:
        photo.order = request.form["order-" + str(photo.id)]
        db.session.add(photo)
    db.session.commit()
    flash(u'更改已保存。', 'success')
    return redirect(url_for('.album', id=id))
# 删除相册
@main.route('/delete/album/<id>')
@login_required
def delete_album(id):
    album=Album.query.filter_by(id=id).first_or_404()
    if album==None:
        abort(404)
    if album.author.username!=current_user.username:
        abort(403)
    db.session.delete(album)
    db.session.commit()
    return redirect(url_for('.albums', username=album.author.username))


# 取消喜欢某个相册
@main.route('/album/unlike/<id>')
@login_required
def unlike_album(id):
    album = Album.query.filter_by(id=id).first()
    if album is None:
        flash(u'无效的相册。', 'warning')
        return redirect(url_for('.likes', username=current_user.username))
    if current_user.is_like_album(album):
        current_user.unlike_album(album)
    return (''), 204

# 取消喜欢某个照片
@main.route('/photo/unlike/<id>')
@login_required
#@permission_required(Permission.FOLLOW)
def unlike_photo(id):
    # unlike photo in likes page.
    photo = Photo.query.filter_by(id=id).first()
    if photo is None:
        flash(u'无效的图片。', 'warning')
        return redirect(url_for('.likes', username=current_user.username))
    if current_user.is_like_photo(photo):
        current_user.unlike_photo(photo)
    return (''), 204

# 编辑照片的页面 删除照片
@main.route('/delete/edit-photo/<id>')
@login_required
def delete_edit_photo(id):
    photo = Photo.query.filter_by(id=id).first()
    if photo is None:
        flash(u'无效的操作。', 'warning')
        return redirect(url_for('.index', username=current_user.username))
    if current_user.username != photo.author.username:
        abort(403)
    db.session.delete(photo)
    db.session.commit()
    return (''), 204

@main.route('/delete/photo/<id>')
@login_required
def delete_photo(id):
    photo = Photo.query.filter_by(id=id).first()
    album = photo.album
    if photo is None:
        flash(u'无效的操作。', 'warning')
        return redirect(url_for('.index', username=current_user.username))
    if current_user.username != photo.author.username:
        abort(403)
    db.session.delete(photo)
    db.session.commit()
    flash(u'删除成功。', 'success')
    return redirect(url_for('.album', id=album.id))


@main.route('/setting', methods=['GET', 'POST'])
@login_required
def setting():
    form = SettingForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.location = form.location.data
        current_user.website = form.website.data
        current_user.about_me = form.about_me.data
        current_user.like_public = form.like_public.data
        flash(u'你的设置已经更新。', 'success')
        return redirect(url_for('.albums', username=current_user.username))
    form.username.data = current_user.username
    form.location.data = current_user.location
    form.website.data = current_user.website
    form.about_me.data = current_user.about_me
    form.like_public.data = current_user.like_public
    return render_template('setting.html', form=form, user=current_user)
