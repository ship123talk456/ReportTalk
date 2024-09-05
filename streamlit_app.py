import streamlit as st
import sqlite3
import bcrypt
import pandas as pd

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
    st.subheader('注册公司账号')
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
        else:
            st.error('公司名称或密码错误。')

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

        c.execute('INSERT INTO ships (company_id, ship_name, imo_number, mmsi) VALUES (?, ?, ?, ?)',
                  (st.session_state['company_id'], ship_name, imo_number, mmsi))
        conn.commit()
        st.success('船舶添加成功！')

    # 显示当前公司配置的船舶
    st.write('当前已配置的船舶：')
    ships = c.execute('SELECT ship_name, imo_number, mmsi FROM ships WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()
    st.table(pd.DataFrame(ships, columns=['船舶名称', 'IMO编号', 'MMSI']))

# 报告模板配置功能
def configure_report_templates():
    st.subheader('报告模板配置')
    report_type = st.selectbox('报告类型', ['早报', '午报', '晚报', '离港报', '抵港报', '航次报'])
    fields = st.text_area('报告字段（用逗号分隔）', '航次编号,填报日期,船舶位置,平均航速,24小时耗油量,船舶燃油存量,24小时航行里程,剩余航行里程,预计抵港时间,始发港,目的港')

    if st.button('配置模板'):
        c.execute('INSERT INTO report_templates (company_id, report_type, fields) VALUES (?, ?, ?)',
                  (st.session_state['company_id'], report_type, fields))
        conn.commit()
        st.success('模板配置成功！')

    # 显示当前公司的报告模板
    st.write('当前已配置的报告模板：')
    templates = c.execute('SELECT report_type, fields FROM report_templates WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()
    st.table(pd.DataFrame(templates, columns=['报告类型', '报告字段']))

# 报告填报功能
def fill_report():
    st.subheader('报告填报')
    
    # 选择船舶和报告类型
    ship_name = st.selectbox('选择船舶', [s[0] for s in c.execute('SELECT ship_name FROM ships WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()])
    report_type = st.selectbox('选择报告类型', [t[0] for t in c.execute('SELECT report_type FROM report_templates WHERE company_id = ?', (st.session_state['company_id'],)).fetchall()])

    # 获取船舶ID
    ship_id = c.execute('SELECT id FROM ships WHERE ship_name = ? AND company_id = ?', (ship_name, st.session_state['company_id'])).fetchone()
    if ship_id:
        ship_id = ship_id[0]
    else:
        st.error('未找到船舶ID')
        return

    # 获取报告字段
    fields = c.execute('SELECT fields FROM report_templates WHERE report_type = ? AND company_id = ?', (report_type, st.session_state['company_id'])).fetchone()
    if fields:
        fields = fields[0].split(',')
    else:
        st.error('未找到报告模板字段')
        return

    # 填报字段
    report_data = {field: st.text_input(field) for field in fields}

    if st.button('保存报告'):
        c.execute('INSERT INTO reports (ship_id, report_type, data, status) VALUES (?, ?, ?, ?)', (ship_id, report_type, str(report_data), 'saved'))
        conn.commit()
        st.success('报告保存成功！')

    if st.button('提交报告'):
        c.execute('UPDATE reports SET status = ? WHERE ship_id = ? AND report_type = ? AND status = ?', ('submitted', ship_id, report_type, 'saved'))
        conn.commit()
        st.success('报告提交成功！')


# 报告查阅功能
def view_reports():
    st.subheader('报告查阅')
    reports = c.execute('SELECT id, ship_id, report_type, data, status FROM reports').fetchall()
    report_df = pd.DataFrame(reports, columns=['ID', '船舶ID', '报告类型', '数据', '状态'])
    st.dataframe(report_df)

    # 筛选与查阅
    selected_report_id = st.selectbox('选择查看的报告ID', report_df['ID'])
    selected_report = report_df.loc[report_df['ID'] == selected_report_id]
    st.write(f"报告详细信息：{selected_report.to_dict()}")

# Streamlit主界面逻辑
def main():
    st.title('航运公司报告管理系统')

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        st.sidebar.header('导航')
        page = st.sidebar.radio('选择功能', ['船舶配置', '报告模板配置', '报告填报', '报告查阅'])

        if page == '船舶配置':
            configure_ships()
        elif page == '报告模板配置':
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
