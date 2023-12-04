
from flask import request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# 从 flask 包导入 Flask 类，通过实例化这个类，创建一个程序对象 app:
from markupsafe import escape
from datetime import datetime
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy  # 导入扩展类
from sqlalchemy import text
app = Flask(__name__)
import pymysql
from sqlalchemy import or_
app.secret_key = '123'

login_manager = LoginManager(app)  # 实例化扩展类
login_manager.login_view = 'login'
import click

# 数据库配置
# 在app.config中设置好连接数据库的信息
# 然后使用SQLALchemy(app)创建一个db对象
# SQLAlchemy会自动读取app.config中连接数据库的信息

# MySQL所在的主机名
HOSTNAME = "localhost"
# MySQL监听的端口号，默认3306
PORT = 3306
# 连接MySQL的用户名
USERNAME = "root"
# 连接MySQL的密码
PASSWORD = "root"
# MySQL上创建的数据库名称
DATABASE = "mywatchlist"

app.config['SQLALCHEMY_DATABASE_URI']= f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}?charset=utf8mb4"
db = SQLAlchemy(app)  # 初始化扩展，传入程序实例 app

'''
# 测试数据库连接
with app.app_context():
    with db.engine.connect() as conn:
        rs = conn.execute(text("select 1"))
        print(rs.fetchone())
        # (1,)
'''


class Movie(db.Model):  # 表名将会是 movie_info
    __tablename__ = "movie_info"
    movie_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 会自动增长的主键
    title = db.Column(db.String(60))  # 电影标题
    release_date = db.Column(db.DateTime)
    country = db.Column(db.String(20))  # 电影国家
    movie_type = db.Column(db.String(10))  # 电影类型
    year = db.Column(db.Integer)  # 电影年份

class MovieBox(db.Model): # 存储电影票房的表格
    __tablename__ = 'move_box'
    movie_id = db.Column(db.Integer, db.ForeignKey('movie_info.movie_id'), primary_key=True, autoincrement=True) # 通过db.ForeignKey将movie_id字段与movie_info表中的对应字段进行关联。
    box = db.Column(db.Float) # 电影票房
    movie = db.relationship('Movie', backref=db.backref('movie_box', cascade='all, delete-orphan'))

class ActorInfo(db.Model):
    __tablename__ = 'actor_info'
    actor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    actor_name = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(2), nullable=False)
    actor_country = db.Column(db.String(20))

class MovieActorRelation(db.Model):
    __tablename__ = 'movie_actor_relation'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    movie_id = db.Column(db.Integer,  db.ForeignKey('movie_info.movie_id'), nullable=False, autoincrement=True) # 对应字段进行关联
    actor_id = db.Column(db.Integer, db.ForeignKey('actor_info.actor_id'), nullable=False, autoincrement=True)
    relation_type = db.Column(db.String(20)) # 主演还是导演
    movie = db.relationship('Movie', backref=db.backref('movie_actor_relations', cascade='all, delete-orphan'))
    actor = db.relationship('ActorInfo', backref=db.backref('movie_actor_relations', cascade='all, delete-orphan'))
'''
with app.app_context():
    # 创建电影和演员对象
    movie = Movie(title='电影标题', release_date=datetime.now(), country='电影国家', movie_type='电影类型', year=2022)
    actor = ActorInfo(actor_name='演员姓名', gender='性别', actor_country='演员国家')
    # 创建电影和演员的关联关系对象
    relation = MovieActorRelation(movie_id=movie.movie_id, actor_id=actor.actor_id, relation_type='主演')
    # 创建电影票房信息对象
    movie_box = MovieBox(movie_id=movie.movie_id, box=1000000.0)
    # 将对象添加到数据库会话中
    db.session.add(movie)
    db.session.add(actor)
    db.session.add(movie_box)
    db.session.add(relation)
'''

class User(db.Model, UserMixin):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20))
    username = db.Column(db.String(20))  # 用户名
    password_hash = db.Column(db.String(256))  # 密码哈希值
    def set_password(self, password):  # 用来设置密码的方法，接受密码作为参数
        self.password = password  # 将明文密码存储在 password 字段中
        self.password_hash = generate_password_hash(password)  # 将生成的密码哈希值存储在 password_hash 字段中
    def validate_password(self, password):  # 用于验证密码的方法，接受密码作为参数
        return check_password_hash(self.password_hash, password)  # 返回布尔值


# 在设置了数据库的前提下，负责显示主页的 index 可以从数据库里读取真实的数据：
@app.route('/', methods=['GET', 'POST'])
def index():
    # 创建电影条目
    if request.method == 'POST':  # 判断是否是 POST 请求
        # 获取表单数据
        if not current_user.is_authenticated:  # 如果当前用户未认证
            return redirect(url_for('index'))  # 重定向到主页
        title = request.form.get('title')
        release_date = request.form.get('release_date')
        country = request.form.get('country')
        movie_type = request.form.get('movie_type')
        year = int(request.form.get('year'))
        actor_name = request.form.get('actor_name')
        relation_type = request.form.get('relation_type')
        actor_country = request.form.get('actor_country')
        gender = request.form.get('gender')
        box_value = request.form.get('box')
        if box_value:
            box = float(box_value)
        else:
            box = None  # 或者其他你认为合适的默认值
        # 验证数据
        if release_date == '':
            release_date = '9999/01/01'  # 使用 "9999/01/01" 替代空字符串

        release_date = datetime.strptime(release_date, '%Y/%m/%d')
        if not title or not year or not country or not movie_type or len(str(year)) > 4 or len(title) > 60:
            flash('Invalid input.')  # 显示错误提示
            return redirect(url_for('index'))  # 重定向回主页
        # 保存表单数据到数据库
        movie = Movie(title=title, release_date=release_date, country=country, movie_type=movie_type, year=year)  # 创建记录
        # 创建演员对象
        db.session.add(movie) # 添加到数据库会话
        db.session.commit()  # # 提交数据库会话，保存关联关系和电影票房信息
        actor = ActorInfo(actor_name=actor_name, gender=gender, actor_country=actor_country)
        # 创建电影票房信息对象
        db.session.add(actor)
        db.session.commit()  # # 提交数据库会话，保存关联关系和电影票房信息
        movie_box = MovieBox(movie_id=movie.movie_id, box=box)
        # 创建电影和演员的关联关系对象
        relation = MovieActorRelation(movie_id=movie.movie_id, actor_id=actor.actor_id, relation_type=relation_type)
        # 将对象添加到数据库会话中
        db.session.add(movie_box)
        db.session.add(relation)
        db.session.commit()  # # 提交数据库会话，保存关联关系和电影票房信息
        flash('Item created.')  # 显示成功创建的提示
        return redirect(url_for('index'))  # 重定向回主页
    movie_info = Movie.query.all()
    return render_template('index.html', movies=movie_info)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)  # 设置密码
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password)  # 设置密码
        db.session.add(user)
    db.session.commit()  # 提交数据库会话
    click.echo('Done.')

@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required  # 登录保护
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':  # 处理编辑表单的提交请求
        if not current_user.is_authenticated:  # 如果当前用户未认证
            return redirect(url_for('index'))  # 重定向到主页
            flash('Is not authenticated.')
        # 获取表单数据
        title = request.form.get('title')
        release_date = request.form.get('release_date')
        country = request.form.get('country')
        movie_type = request.form.get('movie_type')
        year = int(request.form.get('year'))
        actor_name = request.form.get('actor_name')
        relation_type = request.form.get('relation_type')
        actor_country = request.form.get('actor_country')
        gender = request.form.get('gender')
        box_value = request.form.get('box')
        if box_value:
            box = float(box_value)
        else:
            box = None  # 或者其他你认为合适的默认值
        # 验证数据
        if release_date == '':
            release_date = '9999/01/01'  # 使用 "9999/01/01" 替代空字符串

        release_date = datetime.strptime(release_date, '%Y/%m/%d')
        if not title or not year or not country or not movie_type or len(str(year)) > 4 or len(title) > 60:
            flash('Invalid input.')  # 显示错误提示
            return redirect(url_for('index'))  # 重定向回主页
        # 更新电影信息
        movie.title = title
        movie.release_date = release_date
        movie.country = country
        movie.movie_type = movie_type
        movie.year = year
        # 更新演员信息
        if movie.movie_actor_relations:
            for relation in movie.movie_actor_relations:
                if relation.actor:
                    relation.actor.actor_name = actor_name
                    relation.actor.gender = gender
                    relation.actor.actor_country = actor_country
        # 更新票房信息
        if movie.movie_box:
            movie.movie_box.box = box
        # 更新电影和演员的关联关系
        if movie.movie_actor_relations:
            for relation in movie.movie_actor_relations:
                relation.relation_type = relation_type
        # 提交数据库会话，保存更新后的信息
        db.session.commit()
        flash('Item updated.')
        return redirect(url_for('index'))  # 重定向回主页
    return render_template('edit.html', movie=movie, actor_info=movie.movie_actor_relations, move_box=movie.movie_box)

@app.route('/movie/delete/<int:movie_id>', methods=['POST'])  # 限定只接受 POST 请求
@login_required  # 登录保护
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)  # 获取电影记录
    db.session.delete(movie)  # 删除对应的记录
    db.session.commit()  # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index'))  # 重定向回主页


@app.context_processor
def inject_user():
    user = User.query.first()
    return dict(user=user)

@login_manager.user_loader
def load_user(user_id):  # 创建用户加载回调函数，接受用户 ID 作为参数
    user = User.query.get(int(user_id))  # 用 ID 作为 User 模型的主键查询对应的用户
    return user  # 返回用户对象


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()
        if user and user.validate_password(password):
            login_user(user)
            flash('Login success.')
            return redirect(url_for('index'))


        flash('Invalid username or password.')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
@login_required  # 用于视图保护，后面会详细介绍
def logout():
    logout_user()  # 登出用户
    flash('Goodbye.')
    return redirect(url_for('index'))  # 重定向回首页


# 为程序添加一个设置页面，支持修改用户的名字：
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']

        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))

        current_user.name = name
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用法
        # user = User.query.first()
        # user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))

    return render_template('settings.html')



# 使用MarkupSafe（Flask 的依赖之一）提供的 escape() 函数对 name 变量进行转义处理，比如把 < 转换成 &lt;。这样在返回响应时浏览器就不会把它们当做代码执行。
@app.route('/user/<name>')
def user_page(name):
    return f'User: {escape(name)}'


# 搜索结果界面的渲染
@app.route('/search', methods=['GET', 'POST'])
def search():
    search_term = request.form.get('search_term')
    year = request.form.get('year')
    movie_type = request.form.get('movie_type')
    country = request.form.get('country')
    actor = request.form.get('actor')

    # 构建查询
    query = Movie.query

    if search_term:
        query = query.filter(Movie.title.ilike(f'%{search_term}%'))
    if year:
        query = query.filter(Movie.year == year)
    if movie_type:
        query = query.filter(Movie.movie_type == movie_type)
    if country:
        query = query.filter(Movie.country.ilike(f'%{country}%'))
    if actor:
        query = query.join(Movie.movie_actor_relations).join(MovieActorRelation.actor).filter(ActorInfo.actor_name.ilike(f'%{actor}%'))

    # 执行查询并获取结果
    movies = query.all()
    return render_template('search_results.html', movies=movies)

# 在搜索界面定义返回函数
@app.route('/back')
def back():
    return render_template('index.html')


'''
with app.app_context():
    # db.create_all() # 创建表
    db.session.commit() # 提交数据库会话
'''
'''
# 创建应用上下文
with app.app_context():
    # 删除表
    db.drop_all()
'''
