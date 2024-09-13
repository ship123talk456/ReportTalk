import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

import streamlit as st

# Set page configuration (optional, does not affect icons)
st.set_page_config(page_title="Your App Title", page_icon=":chart_with_upwards_trend:")

# Use CSS to hide the icons
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;} /* Hides Share, Star, GitHub icons */
    .stActionButton {display: none !important;} /* General hide for buttons */
    .styles_terminalButton__JBj5T {display: none !important;}
    </style>
    """,
    unsafe_allow_html=True
)

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
            st.session_state['company_id'] = result[0]
            st.success('登录成功！')
            st.rerun()  # 刷新页面         
        else:
            st.error('公司名称或密码错误。')

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
    
        # 显示船舶列表和删除按钮
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
            # 删除按钮
            if st.button(f'删除', key=f"delete_{row[0]}"):
                if st.session_state.get(f'confirm_delete_{row[0]}', False):
                    delete_ship(row[0])
                    st.success(f'船舶 {row[1]} 删除成功！')
                    st.session_state.pop(f'confirm_delete_{row[0]}', None)
                    st.rerun()  # 刷新页面
                else:
                    # 弹出确认删除的模态窗口
                    with st.modal(key=f'modal_confirm_delete_{row[0]}'):
                        st.warning(f'确认删除船舶 {row[1]} 吗？再次点击删除按钮确认删除。')
                        # 设置确认状态为 True，表示确认删除
                        st.session_state[f'confirm_delete_{row[0]}'] = True


    # 如果删除后仍然存在船舶，显示表格
    if st.session_state['ships']:
        df_ships = pd.DataFrame(st.session_state['ships'], columns=['ID', '船舶名称', 'IMO编号', 'MMSI'])
        st.table(df_ships)
    else:
        st.write("没有配置船舶。")


# 获取当前公司配置的报告模板
def get_templates():
    return c.execute(
        'SELECT id, report_type, fields FROM report_templates WHERE company_id = ?',
        (st.session_state['company_id'],)
    ).fetchall()

# 删除报告模板函数
def delete_template(template_id):
    c.execute('DELETE FROM report_templates WHERE id = ?', (template_id,))
    conn.commit()
    # 更新 session_state 中的模板数据
    st.session_state['templates'] = get_templates()


# 报告模板配置功能
def configure_report_templates():
    st.subheader('报告模板配置')
    report_type = st.selectbox('报告类型', ['早报', '午报', '晚报', '离港报', '抵港报', '航次报'])
    fields = st.text_area('报告字段（用逗号分隔）', '航次编号,填报日期,船舶位置,平均航速,24小时耗油量,船舶燃油存量,24小时航行里程,剩余航行里程,预计抵港时间,始发港,目的港')

    if st.button('配置模板'):
       # 检查该报告类型是否已存在
        existing_template = c.execute(
            'SELECT id FROM report_templates WHERE company_id = ? AND report_type = ?',
            (st.session_state['company_id'], report_type)
        ).fetchone()

        if existing_template:
            # 提示用户确认是否替换
            if st.session_state.get('confirm_replace', False):
                # 如果用户确认替换，执行更新操作
                c.execute(
                    'UPDATE report_templates SET fields = ? WHERE id = ?',
                    (fields, existing_template[0])
                )
                conn.commit()
                st.success('已替换旧的报告模板！')
                st.session_state.pop('confirm_replace', None)
                # 刷新模板列表
                st.session_state['templates'] = get_templates()
                st.rerun()
            else:
                # 设置确认状态并提醒用户是否替换
                st.session_state['confirm_replace'] = True
                st.warning(f'报告类型 {report_type} 已经存在。点击配置模板按钮再次确认替换。')
        else:
            # 如果没有冲突，直接插入新的模板
            c.execute(
                'INSERT INTO report_templates (company_id, report_type, fields) VALUES (?, ?, ?)',
                (st.session_state['company_id'], report_type, fields)
            )
            conn.commit()
            st.success('模板配置成功！')
            # 刷新模板列表
            st.session_state['templates'] = get_templates()
            st.rerun()


    # 初始化模板数据到 session_state
    if 'templates' not in st.session_state:
        st.session_state['templates'] = get_templates()

    # 显示当前公司的报告模板
    st.write('当前已配置的报告模板：')

    # 显示模板列表和删除按钮
    for index, row in enumerate(st.session_state['templates']):
        # 调整列的比例，确保删除按钮有足够的显示空间
        col1, col2, col3 = st.columns([2, 6, 2])
        with col1:
            st.write(row[1])  # 显示报告类型
        with col2:
            st.write(row[2])  # 显示报告字段
        with col3:
            # 添加删除按钮，并确保每个按钮有唯一的 key
            delete_button = st.button(f'删除', key=f"delete_template_{row[0]}")
            if delete_button:
                if st.session_state.get(f'confirm_delete_template_{row[0]}', False):
                    delete_template(row[0])
                    st.success(f'报告模板 {row[1]} 删除成功！')
                    st.session_state.pop(f'confirm_delete_template_{row[0]}', None)
                    st.rerun()  # 刷新页面
                else:
                    # 设置确认状态，并弹出确认删除的信息
                    st.session_state[f'confirm_delete_template_{row[0]}'] = True
                    st.warning(f'确认删除报告模板 {row[1]} 吗？再次点击按钮确认删除。')

    # 检查模板是否成功显示
    if not st.session_state['templates']:
        st.write("没有配置报告模板。")

    # 显示删除后的模板列表
    if st.session_state['templates']:
        df_templates = pd.DataFrame(st.session_state['templates'], columns=['ID', '报告类型', '报告字段'])
        st.table(df_templates.drop(columns=['ID']))  # 隐藏ID列，仅显示报告类型和字段
    else:
        st.write("没有配置报告模板。")

      
def fill_report():
    st.subheader('报告填报')
    
    # 选择船舶和报告类型
    ship_name = st.selectbox(
        '选择船舶', 
        [s[0] for s in c.execute('SELECT ship_name FROM ships WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()]
    )
    report_type = st.selectbox(
        '选择报告类型', 
        [t[0] for t in c.execute('SELECT report_type FROM report_templates WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()]
    )

    # 获取船舶ID
    ship_id = c.execute(
        'SELECT id FROM ships WHERE ship_name = ? AND company_id = ?', 
        (ship_name, st.session_state['company_id'])
    ).fetchone()
    if ship_id:
        ship_id = ship_id[0]
    else:
        st.error('未找到船舶ID')
        return

    # 获取报告字段
    fields = c.execute(
        'SELECT fields FROM report_templates WHERE report_type = ? AND company_id = ?', 
        (report_type, st.session_state['company_id'])
    ).fetchone()
    if fields:
        fields = fields[0].split(',')
    else:
        st.error('未找到报告模板字段')
        return

    # 初始化报告数据
    if 'report_data' not in st.session_state:
        st.session_state['report_data'] = {}

    # 确保所有字段都被初始化
    for field in fields:
        if field not in st.session_state['report_data']:
            st.session_state['report_data'][field] = ''  # 初始化为默认空字符串

    # 填报字段
    for field in fields:
        st.session_state['report_data'][field] = st.text_input(
            field, value=st.session_state['report_data'][field]
        )

    # 用户输入的收件人邮箱地址
    recipient_email = st.text_input('请输入收件人邮箱地址')

    # 自动保存报告数据
    if 'saved_report_id' not in st.session_state:
        # 保存初始报告
        c.execute(
            'INSERT INTO reports (ship_id, report_type, data, status) VALUES (?, ?, ?, ?)', 
            (ship_id, report_type, str(st.session_state['report_data']), 'saved')
        )
        conn.commit()
        st.session_state['saved_report_id'] = c.lastrowid
        st.success('报告已自动保存！')
    else:
        # 更新已保存的报告
        c.execute(
            'UPDATE reports SET data = ? WHERE id = ? AND status = ?', 
            (str(st.session_state['report_data']), st.session_state['saved_report_id'], 'saved')
        )
        conn.commit()
        st.success('报告内容已更新并自动保存！')

    # 提交报告
    if st.button('提交报告'):
        c.execute(
            'UPDATE reports SET status = ? WHERE id = ?', 
            ('submitted', st.session_state['saved_report_id'])
        )
        conn.commit()
        st.success('报告提交成功！')

        # 发送邮件
        if recipient_email:
            subject = f"提交的报告 - {ship_name} - {report_type}"
            message_text = f"以下是您提交的报告内容:\n\n{str(st.session_state['report_data'])}"
            send_email(subject, message_text, recipient_email)
            st.success('邮件已发送至: ' + recipient_email)
        else:
            st.error('请填写收件人邮箱地址')

        # 清空保存状态
        del st.session_state['saved_report_id']


# 发送邮件
def send_email(subject, message_text, to_email):
    sender_email = "ship_talk@163.com"
    sender_password = "NXOXBFCTOLWWRSSI"  # 请替换为您的邮箱密码或应用专用密码

    # 创建 MIME 多部分消息对象
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # 添加邮件正文
    msg.attach(MIMEText(message_text, 'plain'))

    # 连接到 SMTP 服务器并发送邮件
    server = smtplib.SMTP_SSL('smtp.163.com', 465)  # 使用 SSL
    server.login(sender_email, sender_password)
    server.send_message(msg)
    server.quit()      


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
    #st.title('船舶报告系统')
    # 引入 Font Awesome
    st.markdown(
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">',
        unsafe_allow_html=True
    )
    #st.sidebar.markdown("<h1 style='font-size:30px;'>船舶报告系统</h1>", unsafe_allow_html=True)
    # 使用 HTML 来设置侧边栏的标题样式，并添加船舶图标
    st.sidebar.markdown(
        '<h1 style="font-size:30px;"><i class="fas fa-ship"></i> 船舶报告系统</h1>',
        unsafe_allow_html=True
    )

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
     
    
    if st.session_state['logged_in']:
        #st.sidebar.header('船舶报告系统')
        page = st.sidebar.radio('选择功能', ['船舶配置', '模板配置', '报告填报', '报告查阅'])
     

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
        action = st.sidebar.radio('选择操作', ['登录', '注册'])

        if action == '登录':
            login()
        elif action == '注册':
            register_company()  
    

if __name__ == '__main__':
    main()
        

