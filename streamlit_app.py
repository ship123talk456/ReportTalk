import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# 设置数据库连接
conn = sqlite3.connect('shipping_system.db')
c = conn.cursor()

# 数据库初始化函数
def init_db():
    c.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE,
            password BLOB
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            ship_name TEXT,
            imo_number TEXT,
            mmsi TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS report_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            report_type TEXT,
            fields TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ship_id INTEGER,
            report_type TEXT,
            data TEXT,
            status TEXT, -- 保存状态：saved, submitted
            FOREIGN KEY (ship_id) REFERENCES ships(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password BLOB
        )
    ''')
    conn.commit()

# 初始化数据库
init_db()

# 用户注册功能
def register_company():
    st.subheader('注册')
    company_name = st.text_input('公司名称')
    password = st.text_input('密码（需包含字母、符号和数字）', type='password')

    if st.button('注册'):
        if not company_name or not password:
            st.error('请输入公司名称和密码。')
            return

        # 密码复杂性检查
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password) or not any(c in '!@#$%^&*()-+=' for c in password):
            st.error('密码必须包含字母、数字和符号。')
            return

        # 加密密码并存储
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        try:
            c.execute('INSERT INTO companies (company_name, password) VALUES (?, ?)', (company_name, hashed_pw))
            conn.commit()
            st.success('注册成功！')
        except sqlite3.IntegrityError:
            st.error('公司名称已存在。')

# 用户登录功能
def login():
    st.subheader('登录')
    company_name = st.text_input('公司名称')
    password = st.text_input('密码', type='password')

    if st.button('登录'):
        c.execute('SELECT id, password FROM companies WHERE company_name = ?', (company_name,))
        result = c.fetchone()
        if result and bcrypt.checkpw(password.encode(), result[1]):
            st.session_state['logged_in'] = True
            st.session_state['company_id'] = result[0]  # 确保这里设置了 company_id
            st.success('登录成功！')
            st.rerun()  # 刷新页面         
        else:
            st.error('公司名称或密码错误。')

# 注册管理员账号
def register_admin():
    st.subheader('注册管理员')
    username = st.text_input('用户名')
    password = st.text_input('密码（需包含字母、符号和数字）', type='password')

    if st.button('注册'):
        if not username or not password:
            st.error('请输入用户名和密码。')
            return

        # 密码复杂性检查
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password) or not any(c in '!@#$%^&*()-+=' for c in password):
            st.error('密码必须包含字母、数字和符号。')
            return

        # 加密密码并存储
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        try:
            c.execute('INSERT INTO admins (username, password) VALUES (?, ?)', (username, hashed_pw))
            conn.commit()
            st.success('管理员注册成功！')
        except sqlite3.IntegrityError:
            st.error('用户名已存在。')

# 管理员登录功能
def login_admin():
    st.subheader('管理员登录')
    username = st.text_input('用户名')
    password = st.text_input('密码', type='password')

    if st.button('登录'):
        c.execute('SELECT id, password FROM admins WHERE username = ?', (username,))
        result = c.fetchone()
        if result and bcrypt.checkpw(password.encode(), result[1]):
            st.session_state['admin_logged_in'] = True
            st.success('登录成功！')
            st.rerun()  # 刷新页面         
        else:
            st.error('用户名或密码错误。')

# 获取当前公司配置的船舶
def get_ships():
    return c.execute(
        'SELECT id, ship_name, imo_number, mmsi FROM ships WHERE company_id = ?',
        (st.session_state['company_id'],)
    ).fetchall()

# 删除船舶函数
def delete_ship(ship_id):
    c.execute('DELETE FROM ships WHERE id = ?', (ship_id,))
    conn.commit()
    # 更新 session_state 中的船舶数据
    st.session_state['ships'] = get_ships()

# 船舶配置功能
def configure_ships():
    st.subheader('船舶配置')
    ship_name = st.text_input('船舶名称')
    imo_number = st.text_input('IMO编号')
    mmsi = st.text_input('MMSI')

    if st.button('增加船舶'):
        if not ship_name or not imo_number or not mmsi:
            st.error('请填写所有船舶信息。')
            return
        # 添加新船舶到数据库
        c.execute('INSERT INTO ships (company_id, ship_name, imo_number, mmsi) VALUES (?, ?, ?, ?)',
                  (st.session_state['company_id'], ship_name, imo_number, mmsi))
        conn.commit()
        st.success('船舶添加成功！')
        # 更新船舶列表
        st.session_state['ships'] = get_ships()

    # 初始化船舶数据到 session_state
    if 'ships' not in st.session_state:
        st.session_state['ships'] = get_ships()

    # 显示当前公司配置的船舶
    st.write('已配置船舶：')
    for index, row in enumerate(st.session_state['ships']):
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
        with col1:
            st.write(row[0])  # ID
        with col2:
            st.write(row[1])  # 船舶名称
        with col3:
            st.write(row[2])  # IMO编号
        with col4:
            st.write(row[3])  # MMSI
        with col5:
            if st.button(f'删除', key=f"delete_{row[0]}"):
                if st.session_state.get(f'confirm_delete_{row[0]}', False):
                    delete_ship(row[0])
                    st.success(f'船舶 {row[1]} 删除成功！')
                    st.session_state.pop(f'confirm_delete_{row[0]}', None)
                    st.rerun()  # 刷新页面
                else:
                    with st.modal(key=f'modal_confirm_delete_{row[0]}'):
                        st.warning(f'确认删除船舶 {row[1]} 吗？再次点击删除按钮确认删除。')
                        st.session_state[f'confirm_delete_{row[0]}'] = True

    if st.session_state['ships']:
        df_ships = pd.DataFrame(st.session_state['ships'], columns=['ID', '船舶名称', 'IMO编号', 'MMSI'])
        st.table(df_ships)
    else:
        st.write("没有配置船舶。")

# 获取当前公司配置的报告模板
def get_templates():
    company_id = st.session_state.get('company_id')
    if company_id:
        return c.execute(
            'SELECT id, report_type, fields FROM report_templates WHERE company_id = ?',
            (company_id,)
        ).fetchall()
    else:
        # 处理 company_id 不存在的情况
        st.error('公司ID未找到，请确保已登录并设置了公司ID。')
        return []


# 删除报告模板函数
def delete_template(template_id):
    c.execute('DELETE FROM report_templates WHERE id = ?', (template_id,))
    conn.commit()
    st.session_state['templates'] = get_templates()

# 报告模板配置功能
def configure_report_templates():
    st.subheader('报告模板配置')
    report_type = st.selectbox('报告类型', ['早报', '午报', '晚报', '离港报', '抵港报', '航次报'])
    fields = st.text_area('报告字段（用逗号分隔）', '航次编号,填报日期,船舶位置,平均航速,24小时耗油量,船舶燃油存量,24小时航行里程,剩余航行里程,预计抵港时间,始发港,目的港')

    if st.button('配置模板'):
        existing_template = c.execute(
            'SELECT id FROM report_templates WHERE company_id = ? AND report_type = ?',(st.session_state['company_id'], report_type)
        ).fetchone()

    if existing_template:
        if st.session_state.get('confirm_replace', False):
            c.execute(
                'UPDATE report_templates SET fields = ? WHERE id = ?',
                (fields, existing_template[0])
            )
            conn.commit()
            st.success('已替换旧的报告模板！')
            st.session_state.pop('confirm_replace', None)
            st.session_state['templates'] = get_templates()
            st.rerun()
        else:
            st.session_state['confirm_replace'] = True
            st.warning(f'报告类型 {report_type} 已经存在。点击配置模板按钮再次确认替换。')
    else:
        c.execute(
            'INSERT INTO report_templates (company_id, report_type, fields) VALUES (?, ?, ?)',
            (st.session_state['company_id'], report_type, fields)
        )
        conn.commit()
        st.success('模板配置成功！')
        st.session_state['templates'] = get_templates()
        st.rerun()

if 'templates' not in st.session_state:
    st.session_state['templates'] = get_templates()

st.write('当前已配置的报告模板：')
for index, row in enumerate(st.session_state['templates']):
    col1, col2, col3 = st.columns([2, 6, 2])
    with col1:
        st.write(row[1])  # 显示报告类型
    with col2:
        st.write(row[2])  # 显示报告字段
    with col3:
        delete_button = st.button(f'删除', key=f"delete_template_{row[0]}")
        if delete_button:
            if st.session_state.get(f'confirm_delete_template_{row[0]}', False):
                delete_template(row[0])
                st.success(f'报告模板 {row[1]} 删除成功！')
                st.session_state.pop(f'confirm_delete_template_{row[0]}', None)
                st.rerun()
            else:
                st.session_state[f'confirm_delete_template_{row[0]}'] = True
                st.warning(f'确认删除报告模板 {row[1]} 吗？再次点击按钮确认删除。')

if st.session_state['templates']:
    df_templates = pd.DataFrame(st.session_state['templates'], columns=['ID', '报告类型', '报告字段'])
    st.table(df_templates.drop(columns=['ID']))
else:
    st.write("没有配置报告模板。")

def fill_report():
    
    st.subheader('报告填报')
    ship_name = st.selectbox(
    '选择船舶',
    [s[1] for s in c.execute('SELECT ship_name FROM ships WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()]
    )
    report_type = st.selectbox(
    '选择报告类型',
    [t[0] for t in c.execute('SELECT report_type FROM report_templates WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()]
    )
    
    ship_id = c.execute(
        'SELECT id FROM ships WHERE ship_name = ? AND company_id = ?', 
        (ship_name, st.session_state['company_id'])
    ).fetchone()
    if ship_id:
        ship_id = ship_id[0]
    else:
        st.error('未找到船舶ID')
        return
    
    fields = c.execute(
        'SELECT fields FROM report_templates WHERE report_type = ? AND company_id = ?', 
        (report_type, st.session_state['company_id'])
    ).fetchone()
    if fields:
        fields = fields[0].split(',')
    else:
        st.error('未找到报告模板字段')
        return
    
    if 'report_data' not in st.session_state:
        st.session_state['report_data'] = {}
    
    for field in fields:
        if field not in st.session_state['report_data']:
            st.session_state['report_data'][field] = ''  # 初始化为默认空字符串
    
    for field in fields:
        st.session_state['report_data'][field] = st.text_input(
            field, value=st.session_state['report_data'][field]
        )
    
    recipient_email = st.text_input('请输入收件人邮箱地址')
    
    if 'saved_report_id' not in st.session_state:
        c.execute(
            'INSERT INTO reports (ship_id, report_type, data, status) VALUES (?, ?, ?, ?)', 
            (ship_id, report_type, str(st.session_state['report_data']), 'saved')
        )
        conn.commit()
        st.session_state['saved_report_id'] = c.lastrowid
        st.success('报告已自动保存！')
    else:
        c.execute(
            'UPDATE reports SET data = ? WHERE id = ? AND status = ?', 
            (str(st.session_state['report_data']), st.session_state['saved_report_id'], 'saved')
        )
        conn.commit()
        st.success('报告内容已更新并自动保存！')

if st.button('提交报告'):
    c.execute(
        'UPDATE reports SET status = ? WHERE id = ?', 
        ('submitted', st.session_state['saved_report_id'])
    )
    conn.commit()
    st.success('报告提交成功！')

    if recipient_email:
        subject = f"提交的报告 - {ship_name} - {report_type}"
        message_text = f"以下是您提交的报告内容:\n\n{str(st.session_state['report_data'])}"
        send_email(subject, message_text, recipient_email)
        st.success('邮件已发送至: ' + recipient_email)
    else:
        st.error('请填写收件人邮箱地址')

    del st.session_state['saved_report_id']

def send_email(subject, message_text, to_email):
    sender_email = "ship_talk@163.com"
    sender_password = "NXOXBFCTOLWWRSSI"  # 请替换为您的邮箱密码或应用专用密码
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(message_text, 'plain'))
    
    server = smtplib.SMTP_SSL('smtp.163.com', 465)  # 使用 SSL
    server.login(sender_email, sender_password)
    server.send_message(msg)
    server.quit()      

def view_companies_and_ships():
    
    st.subheader('查看船公司和船舶')
    
    if st.session_state.get('admin_logged_in', False):
        companies = c.execute('SELECT * FROM companies').fetchall()
        for company in companies:
            st.write(f"公司名称: {company[1]}")
            ships = c.execute('SELECT * FROM ships WHERE company_id = ?', (company[0],)).fetchall()
        for ship in ships:
            st.write(f"- 船舶名称: {ship[1]}, IMO编号: {ship[2]}, MMSI: {ship[3]}")
        else:
            st.error('请先登录为管理员。')


# 报告查阅功能
def view_reports():
    st.subheader('报告查阅')

    # 查询所有报告，并获取船舶名称
    reports = c.execute(
        '''
        SELECT reports.id, reports.ship_id, ships.ship_name, reports.report_type, reports.data, reports.status
        FROM reports
        JOIN ships ON reports.ship_id = ships.id
        WHERE reports.status = ?
        ''',
        ('submitted',)
    ).fetchall()

    # 将查询结果转为 DataFrame
    report_df = pd.DataFrame(reports, columns=['ID', '船舶ID', '船舶名称', '报告类型', '数据', '状态'])

    # 按报告 ID 倒序排序
    report_df = report_df.sort_values(by='ID', ascending=False)

    # 添加选项“全部”作为默认选项
    ship_names = ['全部'] + report_df['船舶名称'].unique().tolist()

    # 创建选择框，用于选择船舶
    selected_ship_name = st.selectbox('选择查看的船舶名称', ship_names)

    # 根据选择的船舶名称筛选报告，默认显示全部
    if selected_ship_name == '全部':
        filtered_report_df = report_df
    else:
        filtered_report_df = report_df[report_df['船舶名称'] == selected_ship_name]

    # 显示筛选后的报告列表
    for _, row in filtered_report_df.iterrows():
        with st.expander(f"报告 ID: {row['ID']} - {row['报告类型']}"):
            st.write(f"**船舶名称:** {row['船舶名称']}")
            st.write(f"**状态:** {row['状态']}")
            st.write(f"**数据:**")
            st.text_area(f"详细内容 (报告 ID: {row['ID']})", row['数据'], height=200)

# Streamlit主界面逻辑
def main():
    st.set_page_config(page_title="ShipTalk", page_icon=":chart_with_upwards_trend:")
    st.markdown(
        """
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" integrity="sha384-KyZXEAg3QhqLMpG8r+Knujsl5/6en8XCp+HHAAK5GSLf2H2Wz+AU4JZV7dPA" crossorigin="anonymous">
        """,
        unsafe_allow_html=True
    )
    st.sidebar.markdown(
        '<h1 style="font-size:30px;"><i class="fas fa-ship"></i> 船舶报告系统</h1>',
        unsafe_allow_html=True
    )

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

     if st.session_state['logged_in']:
        if 'company_id' in st.session_state:
            page = st.sidebar.radio('🚢选择功能', ['船舶配置', '模板配置', '报告填报', '报告查阅'])
            # 省略其他代码...
        else:
            st.sidebar.error('未找到公司ID。请重新登录。')
            st.session_state['logged_in'] = False  # 重置登录状态
     
        if page == '船舶配置':
            configure_ships()
        elif page == '模板配置':
            configure_report_templates()
        elif page == '报告填报':
            fill_report()
        elif page == '报告查阅':
            view_reports()

        if st.sidebar.button('退出登录'):
            st.session_state['logged_in'] = False
            st.session_state.pop('company_id', None)    

    else:
        st.sidebar.header('账号管理')
        action = st.sidebar.radio('选择操作', ['登录', '注册', '管理员登录'])

        if action == '登录':
            login()
        elif action == '注册':
            register_company()
        elif action == '管理员登录':
            login_admin()

        if st.sidebar.button('注册管理员'):
            register_admin()

        if st.sidebar.button('管理员查看船公司和船舶'):
            view_companies_and_ships()

if __name__ == '__main__':
    main()

