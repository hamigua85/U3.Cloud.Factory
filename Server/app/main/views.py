from flask import render_template, redirect, url_for, abort, flash, request, jsonify, current_app
import datetime, sqlite3, requests, os, threading
import uuid
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm
from app import db
from Common.models import User, Role, Post, File, Task, Permission
from Common.scheduler import get_online_machines, update_online_machine_state
from app.decorators import admin_required

from Common.machine import FDM


ALLOWED_EXTENSIONS = set(['gcode'])


@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
                           pagination=pagination)


@main.route('/post/<int:id>')
def post(id):
    post = Post.query.get_or_404(id)
    return render_template('post.html', posts=[post])


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html', user=user, posts=posts)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def query_uploaded_files():
    files = File.query.filter_by(owner_id=current_user._get_current_object().id).all()
    file_list = []
    for uploaded_file in files:
        temp = uploaded_file.parse_data_to_bootstrap_table()
        file_list.append(temp)
    return file_list


@main.route('/uploaded-files')
@login_required
def uploaded_files():
    file_list = query_uploaded_files()
    return jsonify(file_list)


@main.route('/delete-files')
@login_required
def delete_files():
    filesname = request.args.get('files').split(',')
    for filename in filesname:
        files = File.query.filter_by(name=filename).first()
        db.session.delete(files)
    db.session.commit()
    file_list = query_uploaded_files()
    return jsonify(file_list)


@main.route('/add-tasks')
@login_required
def add_tasks():
    files_id = request.args.get('files').split(',')
    new_task = []
    machine_info = FDM()
    for file_id in files_id:
        file_to_print = File.query.filter_by(id=file_id).first()
        if file_to_print is not None:
            new_task.append(Task(file_id=file_id,
                            start_time=datetime.datetime.now(),
                            progress=0,
                            owner=current_user._get_current_object(),
                            priority=1,
                            state='waiting',
                            machine_info=machine_info.machine_base_info_to_bootstrap_table()))
    for new in new_task:
        db.session.add(new)
    return jsonify()


@main.route('/tasks-info')
@login_required
def task_info():
    tasks_info = Task.query.filter_by().all()
    tasks_info_list = []
    for tasks in tasks_info:
        temp = tasks.parse_data_to_bootstrap_table()
        tasks_info_list.append(temp)
    return jsonify(tasks_info_list)


def check_the_same_filename(filename):
    files = File.query.filter_by(name=filename).all()
    if len(files) > 0:
        return '{0}({1})'.format(filename, len(files) + 1)
    return filename


@main.route('/upload-file', methods=['POST'])
@login_required
def upload_file():
    try:
        upload_files = request.files.getlist('file')
        print('get files')
        for files in upload_files:
            if files and allowed_file(files.filename):
                filename = secure_filename(files.filename)
                uuid_filename = str(uuid.uuid1()).replace('-', '_')
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], uuid_filename)
                files.save(file_path)
                size = os.path.getsize(file_path)
                temp = File(name='{0}'.format(filename),
                            path=file_path,
                            size=size,
                            owner=current_user._get_current_object(),
                            uploaded_time=datetime.datetime.now())
                db.session.add(temp)
    except Exception, e:
        print(e)
    return redirect(url_for('main.task'))


@main.route('/task', methods=['GET'])
@login_required
def task():
    return render_template('tasks.html')


@main.route('/online-machines', methods=['GET', 'POST'])
@login_required
@admin_required
def online_machines():
    if request.method == 'GET':
        cmd = request.args.get('cmd')
        if cmd == 'machine_info':
            machines_info = get_online_machines()
            return jsonify(machines_info)
    return render_template('online_machines.html')


@main.route('/online_machine_state', methods=['POST'])
def online_machine_state():
    if request.method == 'POST':
        update_online_machine_state(request)
        return jsonify()


@main.route('/set_online_machine_state', methods=['GET'])
def set_online_machine_state():
    requests.post("http://{0}:5001/send-cmd?cmd={1}".format(request.args['address'], request.args['cmd']), timeout=5)
    return jsonify()


@main.route('/init_online_machine', methods=['POST'])
def init_online_machine():
    for addr in request.get_json():
        requests.post("http://{0}:5001/init".format(addr), timeout=5)
    return jsonify()
