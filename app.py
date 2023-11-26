from flask import request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# 从 flask 包导入 Flask 类，通过实例化这个类，创建一个程序对象 app:
from markupsafe import escape

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy  # 导入扩展类
# from sqlalchemy import text
app = Flask(__name__)

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
DATABASE = "watchlist"

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


class Movie(db.Model):  # 表名将会是 movies
    __tablename__ = "movie"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 会自动增长的主键
    title = db.Column(db.String(60))  # 电影标题
    year = db.Column(db.String(4))  # 电影年份


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
        title = request.form.get('title')  # 传入表单对应输入字段的 name 值
        year = request.form.get('year')
        # 验证数据
        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')  # 显示错误提示
            return redirect(url_for('index'))  # 重定向回主页
        # 保存表单数据到数据库
        movie = Movie(title=title, year=year)  # 创建记录
        db.session.add(movie)  # 添加到数据库会话
        db.session.commit()  # 提交数据库会话
        flash('Item created.')  # 显示成功创建的提示
        return redirect(url_for('index'))  # 重定向回主页

    movies = Movie.query.all()
    return render_template('index.html', movies=movies)

@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required  # 登录保护
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':  # 处理编辑表单的提交请求
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) != 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))  # 重定向回对应的编辑页面

        movie.title = title  # 更新标题
        movie.year = year  # 更新年份
        db.session.commit()  # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index'))  # 重定向回主页

    return render_template('edit.html', movie=movie)  # 传入被编辑的电影记录

@app.route('/movie/delete/<int:movie_id>', methods=['POST'])  # 限定只接受 POST 请求
@login_required  # 登录保护
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)  # 获取电影记录
    db.session.delete(movie)  # 删除对应的记录
    db.session.commit()  # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index'))  # 重定向回主页

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.context_processor
def inject_user():
    user = User.query.first()
    return dict(user=user)

@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()

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

'''
#  movie_info = Movie(title="战狼2", year="2017", country="中国", type="战争")
@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()
    # 全局的两个变量移动到这个函数内
    name = 'Sobremesala'
    movies = [
        {'title': '速度与激情9', 'year': '2021', 'country': '中国', 'type': '动作'},
        {'title': '长津湖', 'year': '2021', 'country': '中国', 'type': '战争'},
        {'title': '你好，李焕英', 'year': '2021', 'country': '中国', 'type': '喜剧'},
        {'title': '我和我的家乡', 'year': '2020', 'country': '中国', 'type': '剧情'},
        {'title': '姜子牙', 'year': '2020', 'country': '中国', 'type': '动画'},
        {'title': '八佰', 'year': '2020', 'country': '中国', 'type': '战争'},
        {'title': '捉妖记2', 'year': '2018', 'country': '中国', 'type': '喜剧'},
        {'title': '复仇者联盟3', 'year': '2018', 'country': '美国', 'type': '科幻'},
        {'title': '战狼2', 'year': '2017', 'country': '中国', 'type': '战争'},
        {'title': '哪吒之魔童降世', 'year': '2019', 'country': '中国', 'type': '动画'},
        {'title': '流浪地球', 'year': '2019', 'country': '中国', 'type': '科幻'},
        {'title': '复仇者联盟4', 'year': '2019', 'country': '美国', 'type': '科幻'},
        {'title': '红海行动', 'year': '2018', 'country': '中国', 'type': '战争'},
        {'title': '唐人街探案2', 'year': '2018', 'country': '中国', 'type': '喜剧'},
        {'title': '我不是药神', 'year': '2018', 'country': '中国', 'type': '喜剧'},
        {'title': '中国机长', 'year': '2019', 'country': '中国', 'type': '剧情'},
        {'title': '速度与激情8', 'year': '2017', 'country': '美国', 'type': '动作'},
        {'title': '西虹市首富', 'year': '2018', 'country': '中国', 'type': '喜剧'},
    ]
    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie_info = Movie(title=m['title'], year=m['year'], country=m['country'], type=m['type'])
        db.session.add(movie_info)

    db.session.commit()
    click.echo('Done.')
'''

# 使用MarkupSafe（Flask 的依赖之一）提供的 escape() 函数对 name 变量进行转义处理，比如把 < 转换成 &lt;。这样在返回响应时浏览器就不会把它们当做代码执行。
@app.route('/user/<name>')
def user_page(name):
    return f'User: {escape(name)}'



# 搜索结果界面的渲染
@app.route('/search', methods=['POST'])
def search():
    # 根据需要在此处进行搜索结果页面的渲染逻辑
    search_term = request.form.get('search')
    if search_term is not None:
        movies = Movie.query.all()
        filtered_movies = []
        for movie in movies:
            if search_term.lower() in movie.title.lower() or str(movie.year) == search_term:
                filtered_movies.append(movie)

        if filtered_movies:
            flash('successful.')
            return render_template('search_results.html', movies=filtered_movies)

    movies = Movie.query.all()
    flash('fail.')
    return render_template('index.html', movies=movies)


# 增添数据
'''
with app.app_context():
    user = User(name='Grey Li', username='Grey Lii', password_hash='123')  # 创建一个 User 记录
    user1 = User(name='sobremesala', username='sobremesala', password_hash='123')  # 创建一个 User 记录
    db.session.add(user)  # 把新创建的记录添加到数据库会话
    m1 = Movie(title='战狼2', year='2017')  # 创建一个 Movie 记录
    m2 = Movie(title='哪吒之魔童降世', year='2019')  # 再创建一个 Movie 记录
    m3 = Movie(title='流浪地球', year='2019')  # 再创建一个 Movie 记录
    m4 = Movie(title='复仇者联盟4', year='2019')  # 再创建一个 Movie 记录
    m5 = Movie(title='红海行动', year='2018')  # 再创建一个 Movie 记录
    m6 = Movie(title='唐人街探案2', year='2018')  # 再创建一个 Movie 记录
    m7 = Movie(title='我不是药神', year='2018')  # 再创建一个 Movie 记录
    m8 = Movie(title='中国机长', year='2019')  # 再创建一个 Movie 记录
    m9 = Movie(title='速度与激情8', year='2017')  # 再创建一个 Movie 记录
    m10 = Movie(title='西虹市首富', year='2018')  # 再创建一个 Movie 记录
    m11 = Movie(title='复仇者联盟3', year='2018')  # 再创建一个 Movie 记录
    m12 = Movie(title='捉妖记2', year='2018')  # 再创建一个 Movie 记录
    m13 = Movie(title='八佰', year='2020')  # 再创建一个 Movie 记录
    m14 = Movie(title='姜子牙', year='2020')  # 再创建一个 Movie 记录
    m15 = Movie(title='我和我的家乡', year='2020')  # 再创建一个 Movie 记录
    m16 = Movie(title='你好，李焕英', year='2021')  # 再创建一个 Movie 记录
    m17 = Movie(title='长津湖', year='2021')  # 再创建一个 Movie 记录
    m17 = Movie(title='速度与激情9', year='2021')  # 再创建一个 Movie 记录
    db.session.add(m1)
    db.session.add(m2)
    db.session.add(m3)
    db.session.add(m4)
    db.session.add(m5)
    db.session.add(m6)
    db.session.add(m7)
    db.session.add(m8)
    db.session.add(m9)
    db.session.add(m10)
    db.session.add(m11)
    db.session.add(m12)
    db.session.add(m13)
    db.session.add(m14)
    db.session.add(m15)
    db.session.add(m16)
    db.session.add(m17)
    db.session.add(user1)  # 把新创建的记录添加到数据库会话
    db.session.commit()  # 提交数据库会话，只需要在最后调用一次即可
'''



