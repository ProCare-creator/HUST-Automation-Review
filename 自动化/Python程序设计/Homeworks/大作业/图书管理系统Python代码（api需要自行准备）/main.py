import json
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import uuid
import os
from datetime import datetime, timedelta  # 引入时间模块
import httpx
from openai import OpenAI


#关于数据存储 试着用类将数据 隔离起来
class Book:
    def __init__(self, title, author, pubisher, id, is_borrowed=False, borrowed_time=None):
        self.title = title
        self.author = author
        self.pubisher = pubisher
        self.id = id
        self.is_borrowed = is_borrowed
        self.borrowed_time = borrowed_time  # 记录借出时间（字符串格式）

    def to_dict(self):#转化为字典
        return {
            'title': self.title, 'author': self.author,
            'pubisher': self.pubisher, 'id': self.id,
            'is_borrowed': self.is_borrowed, 'borrowed_time': self.borrowed_time
        }


class library_manager:
    def __init__(self):
        self.book_list = []

        self.client = OpenAI(
            api_key="",
            base_url="https://api.deepseek.com",
            http_client=httpx.Client(proxy=None, trust_env=False)
        )#openai 主导的 api 调用格式
        self.load_library_from_json()

    def add_book(self, book):
        self.book_list.append(book)
        self.save_library_to_json() #转化为json 格式 可以保证数据的存储

    def delete_book(self, book_id):
        self.book_list = [b for b in self.book_list if b.id != book_id] #在保留其他数据的基础上 删除不想要的
        self.save_library_to_json()

    def toggle_borrow(self, book_id):
        #借书 + 还书 超期 罚款
        fine_message = ""
        for b in self.book_list:
            if b.id == book_id:
                if b.is_borrowed:
                   if b.borrowed_time:
                        borrow_date = datetime.fromisoformat(b.borrowed_time)
                        days_borrowed = (datetime.now() - borrow_date).days
                        # 限期30天 超天数 每天0.5
                        if days_borrowed > 30:
                            fine_amount = (days_borrowed - 30) * 0.5
                            fine_message = f"该书超期 {days_borrowed - 30} 天，需缴纳罚款：{fine_amount} 元！"

                   b.is_borrowed = False
                   b.borrowed_time = None
                else:

                    b.is_borrowed = True
                    b.borrowed_time = datetime.now().isoformat()  # 记录今天的时间
                break

        self.save_library_to_json()#保存 借书时间
        return fine_message

    def get_ai_intro(self, title):#获取ai输出书籍介绍
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": f"，请用100字以内介绍《{title}》"}],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI 连接失败: {str(e)}"

    def save_library_to_json(self):
        with open('books.json', 'w', encoding='utf-8') as f:
            json.dump([b.to_dict() for b in self.book_list], f, ensure_ascii=False, indent=4)

    def load_library_from_json(self):
        if os.path.exists('books.json'):#检查 books.json 是否存在
            try:
                with open('books.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.book_list = [Book(**b) for b in data]
            except:
                pass


class library_ui:
    def __init__(self):
        self.manager = library_manager()
        self.root = tk.Tk()
        self.root.title('智能图书管理系统')
        self.root.geometry('650x700')
        self.creat_widget()
        self.create_context_menu()
        self.refresh_treeview()

    def create_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)#tearoff=0 防止出现一条奇怪的虚线
        self.menu.add_command(label="📖 AI查询详情😀", command=self.ai_query)
        self.menu.add_command(label="🔄 借阅/归还 (●'◡'●)", command=self.toggle_borrow)
        self.menu.add_separator()
        self.menu.add_command(label="❌ 删除图书 ", command=self.delete_book)

    def creat_widget(self):
        # 顶部：录入与搜索区域
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X, padx=10)

        #书名 作者 录入图书
        tk.Label(top_frame, text='书名').grid(row=0, column=0)
        self.title_Entry = tk.Entry(top_frame, width=15)
        self.title_Entry.grid(row=0, column=1)
        tk.Label(top_frame, text='作者').grid(row=0, column=2)
        self.author_Entry = tk.Entry(top_frame, width=15)
        self.author_Entry.grid(row=0, column=3)
        tk.Button(top_frame, text='录入新书', command=self.add_book, bg="lightblue").grid(row=0, column=4, padx=10)

        # 搜索
        tk.Label(top_frame, text='搜索').grid(row=1, column=0, pady=10)
        self.search_Entry = tk.Entry(top_frame, width=15)
        self.search_Entry.grid(row=1, column=1, columnspan=2, sticky=tk.W)#sticky=tk.W 左对齐
        tk.Button(top_frame, text='🔍 查询', command=self.search_book).grid(row=1, column=3, sticky=tk.W)
        tk.Button(top_frame, text='刷新列表', command=self.refresh_treeview).grid(row=1, column=4)

        # 中间：表格区域
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'title', 'author', 'status', 'date'), show='headings')
        self.tree.heading('id', text='编号');
        self.tree.column('id', width=60)
        self.tree.heading('title', text='书名');
        self.tree.column('title', width=150)
        self.tree.heading('author', text='作者');
        self.tree.column('author', width=100)
        self.tree.heading('status', text='状态');
        self.tree.column('status', width=60)
        self.tree.heading('date', text='借阅日期');
        self.tree.column('date', width=100)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<Button-3>", self.show_menu)

        # --- 底部：AI 显示区域 ---
        self.ai_label = tk.Label(self.root, text="操作说明：右键点击列表中的图书进行操作！！！", fg="blue", wraplength=500,
                                 justify="left")
        self.ai_label.pack(pady=10)

    def show_menu(self, event):
        item = self.tree.identify_row(event.y)#event.y代表鼠标在这个表格区域里，点击的高度坐标
        if item:
            self.tree.selection_set(item) #内部函数：负责把某一行背景涂蓝，并更新“当前被选中的行
            self.menu.post(event.x_root, event.y_root)

    def get_selected_book(self):
        selected = self.tree.selection()#搜索出高亮部分
        if not selected: return None, None #返回两个空值
        values = self.tree.item(selected[0])['values']#selected[0]第一个选中的高亮部分
        return values[0], values[1]

    def search_book(self):
        """执行搜索，只显示匹配的结果"""
        keyword = self.search_Entry.get().lower().strip()
        for item in self.tree.get_children(): self.tree.delete(item)

        for b in self.manager.book_list:
            if keyword in b.title.lower() or keyword in b.author.lower():
                self.insert_book_to_tree(b)

    def insert_book_to_tree(self, b):
        """辅助方法：把书本插入表格"""
        status = '已借出' if b.is_borrowed else '可借阅'
        date_str = b.borrowed_time[:10] if b.borrowed_time else "-"
        self.tree.insert('', tk.END, values=(b.id, b.title, b.author, status, date_str))

    def refresh_treeview(self):
        """刷新列表，显示所有书"""
        for item in self.tree.get_children(): self.tree.delete(item)
        for b in self.manager.book_list:
            self.insert_book_to_tree(b)

    def toggle_borrow(self):
        bid, title = self.get_selected_book()
        fine_msg = self.manager.toggle_borrow(bid)
        self.refresh_treeview()

        if fine_msg:
            # 如果有罚款，弹窗警告
            messagebox.showwarning("归还成功 - 逾期提醒", f"《{title}》归还成功。\n\n⚠️ {fine_msg}")
        else:
            messagebox.showinfo("成功", f"《{title}》借还状态已更新")

    # ... 其他方法 (add_book, delete_book, ai_query) 保持原样 ...
    def ai_query(self):
        bid, title = self.get_selected_book()
        self.ai_label.config(text=f"正在 AI 查询《{title}》...")
        self.root.update()
        intro = self.manager.get_ai_intro(title)
        messagebox.showinfo(f"《{title}》简介", intro)
        self.ai_label.config(text="查询完成")

    def delete_book(self):
        bid, title = self.get_selected_book()
        if messagebox.askyesno("确认", f"确定要永久删除《{title}》吗？"):
            self.manager.delete_book(bid)
            self.refresh_treeview()

    def add_book(self):
        t, a = self.title_Entry.get(), self.author_Entry.get()
        if t and a:
            new_book = Book(t, a, "默认", str(uuid.uuid4())[:8])
            self.manager.add_book(new_book)
            self.refresh_treeview()
            self.title_Entry.delete(0, tk.END);
            self.author_Entry.delete(0, tk.END)

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = library_ui()
    app.run()