import threading
import re
import webbrowser
import tkinter as tk
from tkinter import messagebox

import requests

from client import AgentClient
from config import DEFAULT_SERVER_URL

# Apple-inspired palette
BG = "#F5F5F7"
CARD = "#FFFFFF"
TEXT = "#1D1D1F"
SECONDARY = "#6E6E73"
BORDER = "#D2D2D7"
BLUE = "#007AFF"
BLUE_HOVER = "#0A84FF"
USER_BUBBLE = "#007AFF"
AGENT_BUBBLE = "#E9E9EB"
USER_TEXT = "#FFFFFF"
AGENT_TEXT = "#1D1D1F"
SYSTEM_TEXT = "#8E8E93"
ENTRY_BG = "#FFFFFF"


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master,
        text,
        command,
        width=92,
        height=38,
        radius=19,
        bg=BLUE,
        hover_bg=BLUE_HOVER,
        fg="white",
        font=("Helvetica Neue", 11, "bold"),
        **kwargs,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=master.cget("bg"),
            **kwargs,
        )
        self.command = command
        self.default_bg = bg
        self.hover_bg = hover_bg
        self.radius = radius
        self.button_width = width
        self.button_height = height
        self.text_value = text
        self.fg = fg
        self.font = font
        self.enabled = True

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        self._draw(self.default_bg)

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            **kwargs,
        )

    def _draw(self, fill):
        self.delete("all")
        self._rounded_rect(
            1,
            1,
            self.button_width - 1,
            self.button_height - 1,
            self.radius,
            fill=fill,
            outline=fill,
        )
        self.create_text(
            self.button_width / 2,
            self.button_height / 2,
            text=self.text_value,
            fill=self.fg if self.enabled else "#FFFFFF",
            font=self.font,
        )

    def _on_enter(self, _event):
        if self.enabled:
            self._draw(self.hover_bg)

    def _on_leave(self, _event):
        if self.enabled:
            self._draw(self.default_bg)

    def _on_click(self, _event):
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self._draw(self.default_bg if enabled else "#B0B0B5")


class RoundedEntry(tk.Frame):
    def __init__(
        self,
        master,
        textvariable=None,
        placeholder="",
        width=360,
        height=42,
        **kwargs,
    ):
        super().__init__(master, bg=master.cget("bg"), **kwargs)

        self.placeholder = placeholder
        self.textvariable = textvariable or tk.StringVar()

        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=master.cget("bg"),
        )
        self.canvas.pack(fill="both", expand=True)

        self._rounded_rect(
            1,
            1,
            width - 1,
            height - 1,
            14,
            fill=ENTRY_BG,
            outline=BORDER,
        )

        self.entry = tk.Entry(
            self,
            textvariable=self.textvariable,
            font=("Helvetica Neue", 12),
            relief="flat",
            bd=0,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
        )

        self.canvas.create_window(
            14,
            height / 2,
            anchor="w",
            width=width - 28,
            window=self.entry,
        )

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            **kwargs,
        )

    def bind_return(self, callback):
        self.entry.bind("<Return>", callback)

    def focus_set(self):
        self.entry.focus_set()


class ScrollableChat(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)

        self.canvas = tk.Canvas(
            self,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        self.scrollbar = tk.Canvas(
            self,
            width=12,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self.scrollbar.pack(
            side="right",
            fill="y",
            padx=(0, 4),
            pady=8,
        )

        self.inner = tk.Frame(
            self.canvas,
            bg=BG,
        )

        self.inner_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw",
        )

        self.thumb_id = None
        self.drag_start_y = None
        self.drag_start_first = None

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.scrollbar.bind("<Configure>", lambda _event: self._update_scrollbar())

        # Important: bind on this widget and descendants rather than bind_all only.
        self._bind_wheel(self.canvas)
        self._bind_wheel(self.inner)
        self._bind_wheel(self.scrollbar)

        self.scrollbar.bind("<Button-1>", self._on_scrollbar_click)
        self.scrollbar.bind("<B1-Motion>", self._on_scrollbar_drag)
        self.scrollbar.bind("<ButtonRelease-1>", self._on_scrollbar_release)

        self.canvas.configure(yscrollcommand=self._on_canvas_scroll)

    def _bind_wheel(self, widget):
        # Windows/macOS
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        # Linux/X11
        widget.bind("<Button-4>", self._on_linux_scroll_up, add="+")
        widget.bind("<Button-5>", self._on_linux_scroll_down, add="+")

        # Also bind dynamically when pointer enters child widgets.
        widget.bind("<Enter>", lambda _e: self._activate_wheel_binding(), add="+")

    def _activate_wheel_binding(self):
        root = self.winfo_toplevel()
        root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        root.bind_all("<Button-4>", self._on_linux_scroll_up, add="+")
        root.bind_all("<Button-5>", self._on_linux_scroll_down, add="+")

    def _rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            **kwargs,
        )

    def _on_inner_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.inner_id, width=event.width)
        self._update_scrollbar()

    def _on_canvas_scroll(self, first, last):
        self._update_scrollbar(float(first), float(last))

    def _update_scrollbar(self, first=None, last=None):
        if not self.winfo_exists():
            return

        self.scrollbar.delete("all")

        height = max(self.scrollbar.winfo_height(), 1)
        width = max(self.scrollbar.winfo_width(), 1)

        if first is None or last is None:
            first, last = self.canvas.yview()

        first = float(first)
        last = float(last)

        if first <= 0.0 and last >= 1.0:
            self.thumb_id = None
            return

        track_top = 2
        track_bottom = height - 2
        track_height = max(track_bottom - track_top, 1)

        thumb_top = track_top + first * track_height
        thumb_bottom = track_top + last * track_height

        min_thumb = 38
        if thumb_bottom - thumb_top < min_thumb:
            center = (thumb_top + thumb_bottom) / 2
            thumb_top = center - min_thumb / 2
            thumb_bottom = center + min_thumb / 2

            if thumb_top < track_top:
                thumb_top = track_top
                thumb_bottom = track_top + min_thumb

            if thumb_bottom > track_bottom:
                thumb_bottom = track_bottom
                thumb_top = track_bottom - min_thumb

        x1 = 3
        x2 = width - 3
        radius = max((x2 - x1) / 2, 2)

        self.thumb_id = self._rounded_rect(
            self.scrollbar,
            x1,
            thumb_top,
            x2,
            thumb_bottom,
            radius,
            fill="#B8B8BD",
            outline="",
        )

    def _on_mousewheel(self, event):
        if not self.winfo_exists():
            return

        # macOS trackpads can deliver much smaller deltas than Windows wheels.
        delta = event.delta

        if delta == 0:
            return

        if abs(delta) < 120:
            units = -1 if delta > 0 else 1
        else:
            units = int(-delta / 120)

        self.canvas.yview_scroll(units * 3, "units")
        return "break"

    def _on_linux_scroll_up(self, _event):
        self.canvas.yview_scroll(-3, "units")
        return "break"

    def _on_linux_scroll_down(self, _event):
        self.canvas.yview_scroll(3, "units")
        return "break"

    def _thumb_bounds(self):
        if self.thumb_id is None:
            return None
        return self.scrollbar.bbox(self.thumb_id)

    def _on_scrollbar_click(self, event):
        bounds = self._thumb_bounds()

        if bounds:
            _x1, y1, _x2, y2 = bounds
            if y1 <= event.y <= y2:
                self.drag_start_y = event.y
                self.drag_start_first = self.canvas.yview()[0]
                return

        height = max(self.scrollbar.winfo_height(), 1)
        fraction = max(0.0, min(1.0, event.y / height))
        self.canvas.yview_moveto(fraction)
        self._update_scrollbar()

    def _on_scrollbar_drag(self, event):
        if self.drag_start_y is None or self.drag_start_first is None:
            return

        height = max(self.scrollbar.winfo_height(), 1)
        first, last = self.canvas.yview()
        visible_fraction = max(last - first, 0.0001)

        delta_fraction = (event.y - self.drag_start_y) / height
        new_first = self.drag_start_first + delta_fraction * (1 / max(1 - visible_fraction, 0.0001))
        new_first = max(0.0, min(1.0 - visible_fraction, new_first))

        self.canvas.yview_moveto(new_first)

    def _on_scrollbar_release(self, _event):
        self.drag_start_y = None
        self.drag_start_first = None

    def scroll_to_bottom(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1.0)
        self._update_scrollbar()


class RoundedMessageBubble(tk.Canvas):
    URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")

    def __init__(
        self,
        master,
        message,
        is_user=False,
        max_width=520,
    ):
        self.message = message
        self.is_user = is_user
        self.max_width = max_width

        self.font = ("Helvetica Neue", 12)
        self.pad_x = 16
        self.pad_y = 11
        self.radius = 16

        bubble_bg = USER_BUBBLE if is_user else AGENT_BUBBLE
        text_fg = USER_TEXT if is_user else AGENT_TEXT

        temp = tk.Label(
            master,
            text=message,
            font=self.font,
            wraplength=max_width - (self.pad_x * 2),
            justify="left",
            bd=0,
            padx=0,
            pady=0,
        )
        temp.update_idletasks()

        text_width = min(
            max(temp.winfo_reqwidth(), 24),
            max_width - (self.pad_x * 2),
        )
        text_height = max(temp.winfo_reqheight(), 20)
        temp.destroy()

        width = max(
            text_width + self.pad_x * 2,
            self.radius * 2 + 8,
        )
        height = max(
            text_height + self.pad_y * 2,
            self.radius * 2 + 4,
        )

        super().__init__(
            master,
            width=width,
            height=height,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )

        self._draw_rounded_rect(
            1,
            1,
            width - 1,
            height - 1,
            self.radius,
            fill=bubble_bg,
        )

        self.text_widget = tk.Text(
            self,
            wrap="word",
            font=self.font,
            bg=bubble_bg,
            fg=text_fg,
            insertbackground=text_fg,
            selectbackground="#8AB4F8" if not is_user else "#74A9FF",
            selectforeground=text_fg,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            cursor="arrow",
            takefocus=True,
        )

        self.text_widget.insert("1.0", message)

        self.text_widget.bind("<Key>", self._block_edit)
        self.text_widget.bind("<Control-c>", self._copy_selection)
        self.text_widget.bind("<Control-C>", self._copy_selection)

        self._add_link_tags(message, is_user)

        self.create_window(
            self.pad_x,
            self.pad_y,
            anchor="nw",
            width=text_width,
            height=text_height,
            window=self.text_widget,
        )

    def _block_edit(self, event):
        if event.state & 0x4 and event.keysym.lower() == "c":
            return None
        return "break"

    def _copy_selection(self, _event=None):
        try:
            selected = self.text_widget.get(
                tk.SEL_FIRST,
                tk.SEL_LAST,
            )
        except tk.TclError:
            return "break"

        self.clipboard_clear()
        self.clipboard_append(selected)
        return "break"

    def _add_link_tags(self, message, is_user):
        link_color = "#DDEBFF" if is_user else BLUE

        for index, match in enumerate(self.URL_PATTERN.finditer(message)):
            raw_url = match.group(0)
            url = raw_url.rstrip(".,;:!?)]}")
            trim_count = len(raw_url) - len(url)

            start_offset = match.start()
            end_offset = match.end() - trim_count

            tag = f"url_{index}"

            start_index = f"1.0+{start_offset}c"
            end_index = f"1.0+{end_offset}c"

            self.text_widget.tag_add(
                tag,
                start_index,
                end_index,
            )

            self.text_widget.tag_configure(
                tag,
                foreground=link_color,
                underline=True,
            )

            self.text_widget.tag_bind(
                tag,
                "<Enter>",
                lambda _event: self.text_widget.configure(cursor="hand2"),
            )

            self.text_widget.tag_bind(
                tag,
                "<Leave>",
                lambda _event: self.text_widget.configure(cursor="arrow"),
            )

            self.text_widget.tag_bind(
                tag,
                "<Button-1>",
                lambda _event, link=url: self._open_link(link),
            )

    def _open_link(self, url):
        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:
            messagebox.showerror(
                "Unable to open link",
                str(exc),
            )
        return "break"

    def _draw_rounded_rect(
        self,
        x1,
        y1,
        x2,
        y2,
        radius,
        fill,
    ):
        diameter = radius * 2

        self.create_rectangle(
            x1 + radius,
            y1,
            x2 - radius,
            y2,
            fill=fill,
            outline=fill,
        )

        self.create_rectangle(
            x1,
            y1 + radius,
            x2,
            y2 - radius,
            fill=fill,
            outline=fill,
        )

        self.create_oval(
            x1,
            y1,
            x1 + diameter,
            y1 + diameter,
            fill=fill,
            outline=fill,
        )

        self.create_oval(
            x2 - diameter,
            y1,
            x2,
            y1 + diameter,
            fill=fill,
            outline=fill,
        )

        self.create_oval(
            x1,
            y2 - diameter,
            x1 + diameter,
            y2,
            fill=fill,
            outline=fill,
        )

        self.create_oval(
            x2 - diameter,
            y2 - diameter,
            x2,
            y2,
            fill=fill,
            outline=fill,
        )


class MessageBubble(tk.Frame):
    def __init__(
        self,
        master,
        sender,
        message,
        is_user=False,
    ):
        super().__init__(master, bg=BG)

        side = "right" if is_user else "left"

        bubble = RoundedMessageBubble(
            self,
            message,
            is_user=is_user,
            max_width=560,
        )
        bubble.pack(
            side=side,
            padx=22,
            pady=(3, 7),
        )


class ChatGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CI Nurse")
        self.geometry("900x720")
        self.minsize(720, 560)
        self.configure(bg=BG)

        self.client: AgentClient | None = None
        self.busy = False

        self._build_login_view()

    def _clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    # --------------------------------------------------------------
    # Login
    # --------------------------------------------------------------
    def _build_login_view(self):
        self._clear_window()
        self.configure(bg=BG)

        shell = tk.Frame(self, bg=BG)
        shell.pack(
            fill="both",
            expand=True,
        )

        card = tk.Frame(
            shell,
            bg=BG,
            padx=44,
            pady=40,
        )

        card.place(
            relx=0.5,
            rely=0.46,
            anchor="center",
            width=500,
        )

        title = tk.Label(
            card,
            text="CI Nurse",
            font=("Helvetica Neue", 26, "bold"),
            fg=TEXT,
            bg=BG,
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            card,
            text="Connect to your AI agent",
            font=("Helvetica Neue", 12),
            fg=SECONDARY,
            bg=BG,
        )
        subtitle.pack(
            anchor="w",
            pady=(4, 28),
        )

        tk.Label(
            card,
            text="Server",
            font=("Helvetica Neue", 10, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(
            anchor="w",
            pady=(0, 6),
        )

        self.server_var = tk.StringVar(
            value=DEFAULT_SERVER_URL
        )

        self.server_entry = RoundedEntry(
            card,
            textvariable=self.server_var,
            width=410,
            height=44,
        )
        self.server_entry.pack(
            fill="x",
            pady=(0, 18),
        )

        tk.Label(
            card,
            text="Username",
            font=("Helvetica Neue", 10, "bold"),
            fg=TEXT,
            bg=BG,
        ).pack(
            anchor="w",
            pady=(0, 6),
        )

        self.username_var = tk.StringVar()

        self.username_entry = RoundedEntry(
            card,
            textvariable=self.username_var,
            width=410,
            height=44,
        )
        self.username_entry.pack(
            fill="x",
            pady=(0, 22),
        )

        self.username_entry.bind_return(
            lambda _event: self._start_login()
        )

        self.login_button = RoundedButton(
            card,
            text="Continue",
            command=self._start_login,
            width=180,
            height=42,
            radius=18,
        )
        self.login_button.pack(
            anchor="center",
        )

        self.login_status = tk.Label(
            card,
            text="",
            font=("Helvetica Neue", 10),
            fg=SECONDARY,
            bg=BG,
        )
        self.login_status.pack(
            anchor="center",
            pady=(12, 4),
        )

        self.username_entry.focus_set()

    def _start_login(self):
        if self.busy:
            return

        username = self.username_var.get().strip()
        server_url = self.server_var.get().strip()

        if not username:
            messagebox.showwarning(
                "Username required",
                "Please enter a username.",
            )
            return

        if not server_url:
            messagebox.showwarning(
                "Server required",
                "Please enter the server URL.",
            )
            return

        self.client = AgentClient(server_url)

        self._set_login_busy(
            True,
            "Connecting…",
        )

        threading.Thread(
            target=self._login_worker,
            args=(username,),
            daemon=True,
        ).start()

    def _login_worker(self, username):
        try:
            conversation_id = self.client.login(username)

            if conversation_id:
                self.after(
                    0,
                    self._on_login_success,
                    username,
                )
                return

            self.after(
                0,
                self._ask_to_register,
                username,
            )

        except requests.RequestException as exc:
            self.after(
                0,
                self._show_login_error,
                self._request_error(exc),
            )

        except Exception as exc:
            self.after(
                0,
                self._show_login_error,
                str(exc),
            )

    def _ask_to_register(self, username):
        self._set_login_busy(False, "")

        should_register = messagebox.askyesno(
            "Create account",
            f'"{username}" was not found.\n\nCreate a new account?',
        )

        if not should_register:
            return

        self._set_login_busy(
            True,
            "Creating account…",
        )

        threading.Thread(
            target=self._register_worker,
            args=(username,),
            daemon=True,
        ).start()

    def _register_worker(self, username):
        try:
            self.client.register(username)

            self.after(
                0,
                self._on_login_success,
                username,
            )

        except requests.RequestException as exc:
            self.after(
                0,
                self._show_login_error,
                self._request_error(exc),
            )

        except Exception as exc:
            self.after(
                0,
                self._show_login_error,
                str(exc),
            )

    def _on_login_success(self, username):
        self.busy = False
        self._build_chat_view(username)

    def _show_login_error(self, message):
        self._set_login_busy(
            False,
            "Connection failed",
        )

        messagebox.showerror(
            "Login failed",
            message,
        )

    def _set_login_busy(
        self,
        busy,
        status,
    ):
        self.busy = busy

        if hasattr(self, "login_button"):
            self.login_button.set_enabled(
                not busy
            )

        if hasattr(self, "login_status"):
            self.login_status.configure(
                text=status
            )

    # --------------------------------------------------------------
    # Chat
    # --------------------------------------------------------------
    def _build_chat_view(self, username):
        self._clear_window()

        root = tk.Frame(
            self,
            bg=BG,
        )
        root.pack(
            fill="both",
            expand=True,
        )

        # Minimal top row with centered greeting and standalone logout.
        top_actions = tk.Frame(
            root,
            bg=BG,
            height=58,
        )
        top_actions.pack(
            fill="x",
            side="top",
        )
        top_actions.pack_propagate(False)

        greeting = tk.Label(
            top_actions,
            text=f"Hey, {username}",
            font=("Helvetica Neue", 14, "bold"),
            fg=TEXT,
            bg=BG,
        )
        greeting.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

        logout_button = RoundedButton(
            top_actions,
            text="Log out",
            command=self._logout,
            width=92,
            height=36,
            radius=18,
            bg="#E5E5EA",
            hover_bg="#D8D8DD",
            fg=TEXT,
            font=("Helvetica Neue", 10, "bold"),
        )
        logout_button.pack(
            side="right",
            padx=20,
            pady=11,
        )

        # Chat history
        self.chat_area = ScrollableChat(root)
        self.chat_area.pack(
            fill="both",
            expand=True,
            padx=(8, 4),
        )

        self._append_system_message(
            "Conversation ready"
        )

        # Bottom composer area
        composer_outer = tk.Frame(
            root,
            bg=BG,
        )
        composer_outer.pack(
            fill="x",
            side="bottom",
            padx=18,
            pady=(8, 18),
        )

        composer_card = tk.Canvas(
            composer_outer,
            height=118,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        composer_card.pack(
            fill="x",
            expand=True,
        )

        def draw_composer(_event=None):
            composer_card.delete("bg")
            w = composer_card.winfo_width()
            h = composer_card.winfo_height()

            points = [
                22, 1,
                w - 22, 1,
                w - 1, 1,
                w - 1, 22,
                w - 1, h - 22,
                w - 1, h - 1,
                w - 22, h - 1,
                22, h - 1,
                1, h - 1,
                1, h - 22,
                1, 22,
                1, 1,
            ]

            composer_card.create_polygon(
                points,
                smooth=True,
                splinesteps=28,
                fill=CARD,
                outline="#E2E2E7",
                tags="bg",
            )
            composer_card.tag_lower("bg")

        composer_card.bind("<Configure>", draw_composer)

        # Inner input
        self.message_box = tk.Text(
            composer_card,
            height=4,
            wrap="word",
            font=("Helvetica Neue", 12),
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )

        self.input_window = composer_card.create_window(
            18,
            16,
            anchor="nw",
            window=self.message_box,
        )

        self.message_box.bind(
            "<Return>",
            self._on_return,
        )
        self.message_box.bind(
            "<Shift-Return>",
            self._on_shift_return,
        )

        # Modern send button on the right inside the composer.
        self.send_button = RoundedButton(
            composer_card,
            text="Send",
            command=self._send_current_message,
            width=96,
            height=42,
            radius=21,
        )

        self.send_window = composer_card.create_window(
            0,
            0,
            anchor="ne",
            window=self.send_button,
        )

        self.status_label = tk.Label(
            composer_card,
            text="",
            font=("Helvetica Neue", 9),
            fg=SECONDARY,
            bg=CARD,
        )

        self.status_window = composer_card.create_window(
            0,
            0,
            anchor="ne",
            window=self.status_label,
        )

        def resize_composer(event):
            width = event.width

            input_width = max(width - 155, 180)

            composer_card.itemconfigure(
                self.input_window,
                width=input_width,
                height=82,
            )

            composer_card.coords(
                self.send_window,
                width - 18,
                20,
            )

            composer_card.coords(
                self.status_window,
                width - 22,
                72,
            )

            draw_composer()

        composer_card.bind(
            "<Configure>",
            resize_composer,
            add="+",
        )

        self.message_box.focus_set()

    def _append_message(
        self,
        sender,
        message,
        is_user,
    ):
        bubble = MessageBubble(
            self.chat_area.inner,
            sender,
            message,
            is_user=is_user,
        )

        bubble.pack(
            fill="x",
            pady=2,
        )

        self.chat_area.scroll_to_bottom()

    def _append_system_message(self, message):
        wrapper = tk.Frame(
            self.chat_area.inner,
            bg=BG,
        )
        wrapper.pack(
            fill="x",
            padx=24,
            pady=10,
        )

        label = tk.Label(
            wrapper,
            text=message,
            font=("Helvetica Neue", 9),
            fg=SYSTEM_TEXT,
            bg=BG,
            justify="center",
            anchor="center",
            wraplength=520,
        )
        label.pack(
            anchor="center",
        )

        def update_wrap(_event=None):
            # Keep system/error text inside the visible chat width.
            available = max(self.chat_area.winfo_width() - 80, 220)
            label.configure(
                wraplength=min(available, 620)
            )

        self.chat_area.bind(
            "<Configure>",
            update_wrap,
            add="+",
        )

        update_wrap()
        self.chat_area.scroll_to_bottom()

    def _on_return(self, _event):
        if self.busy:
            self.message_box.insert("insert", "\n")
            return "break"

        self._send_current_message()
        return "break"

    def _on_shift_return(self, _event):
        self.message_box.insert(
            "insert",
            "\n",
        )
        return "break"

    def _send_current_message(self):
        if self.busy or not self.client:
            return

        message = self.message_box.get(
            "1.0",
            "end-1c",
        ).strip()

        if not message:
            return

        self.message_box.delete(
            "1.0",
            "end",
        )

        self._append_message(
            "You",
            message,
            True,
        )

        self._set_chat_busy(True)

        threading.Thread(
            target=self._send_worker,
            args=(message,),
            daemon=True,
        ).start()

    def _send_worker(self, message):
        try:
            data = self.client.send_message(
                message
            )

            output = data.get(
                "output"
            )

            if output is None:
                output = (
                    "The server returned no "
                    "'output' field."
                )

            self.after(
                0,
                self._on_agent_response,
                str(output),
            )

        except requests.RequestException as exc:
            self.after(
                0,
                self._on_send_error,
                self._request_error(exc),
            )

        except Exception as exc:
            self.after(
                0,
                self._on_send_error,
                str(exc),
            )

    def _on_agent_response(self, output):
        self._append_message(
            "Agent",
            output,
            False,
        )

        self._set_chat_busy(False)
        self.message_box.focus_set()

    def _on_send_error(self, message):
        self._append_system_message(
            f"Error: {message}"
        )

        self._set_chat_busy(False)

        messagebox.showerror(
            "Message failed",
            message,
        )

    def _set_chat_busy(self, busy):
        self.busy = busy

        # Keep the input box editable while the agent is responding.
        # Only prevent another send until the current request finishes.
        if hasattr(self, "send_button"):
            self.send_button.set_enabled(not busy)

        if hasattr(self, "message_box"):
            self.message_box.configure(state="normal")

        if hasattr(self, "status_label"):
            self.status_label.configure(
                text="Thinking…" if busy else ""
            )

    def _logout(self):
        if self.client:
            self.client.logout()

        self.client = None
        self.busy = False

        self._build_login_view()

    @staticmethod
    def _request_error(exc):
        response = getattr(
            exc,
            "response",
            None,
        )

        if response is not None:
            try:
                detail = response.json().get(
                    "detail"
                )

                if detail:
                    return (
                        f"{response.status_code}: "
                        f"{detail}"
                    )

            except (
                ValueError,
                AttributeError,
            ):
                pass

            body = response.text.strip()

            if body:
                return (
                    f"{response.status_code}: "
                    f"{body}"
                )

        return str(exc)


if __name__ == "__main__":
    app = ChatGUI()
    app.mainloop()
