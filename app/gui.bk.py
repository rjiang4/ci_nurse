import math
import re
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser

import customtkinter as ctk
import requests
from ctk_markdown import CTkMarkdown

from client import AgentClient
from config import DEFAULT_SERVER_URL


# ----------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG = "#F5F5F7"
CARD = "#FFFFFF"
TEXT = "#1D1D1F"
SECONDARY = "#6E6E73"
BORDER = "#D2D2D7"
BLUE = "#007AFF"
BLUE_HOVER = "#0A84FF"
USER_BUBBLE = "#007AFF"
USER_TEXT = "#FFFFFF"
SYSTEM_TEXT = "#8E8E93"

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


# ----------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------

def estimate_text_height(text: str, chars_per_line: int = 70) -> int:
    """Rough pixel height for short plain-text bubbles."""
    lines = 0

    for line in text.splitlines() or [""]:
        lines += max(1, math.ceil(max(len(line), 1) / chars_per_line))

    return max(42, min(360, lines * 21 + 22))


def estimate_markdown_height(markdown: str, chars_per_line: int = 88) -> int:
    """
    Estimate enough height for CTkMarkdown so the outer chat owns scrolling.

    This intentionally over-allocates a little for headings, tables and code.
    """
    visual_lines = 0
    in_code = False

    for line in markdown.splitlines() or [""]:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code = not in_code
            visual_lines += 1
            continue

        wrapped = max(1, math.ceil(max(len(line), 1) / chars_per_line))

        if in_code:
            visual_lines += wrapped
        elif stripped.startswith("#"):
            visual_lines += wrapped + 1
        elif stripped.startswith("|"):
            visual_lines += wrapped + 1
        else:
            visual_lines += wrapped

    # Extra room for margins, table borders, code headers and markdown spacing.
    return max(90, min(2400, visual_lines * 23 + 52))


# ----------------------------------------------------------------------
# User message bubble
# ----------------------------------------------------------------------

class UserMessageBubble(ctk.CTkFrame):
    """Rounded, selectable user bubble with clickable raw URLs."""

    def __init__(self, master, text: str, max_width: int = 560):
        super().__init__(
            master,
            fg_color=USER_BUBBLE,
            corner_radius=18,
            border_width=0,
        )

        self._url_tags: dict[str, str] = {}

        width = min(
            max(130, len(max(text.splitlines() or [text], key=len, default="")) * 8 + 36),
            max_width,
        )
        height = estimate_text_height(text)

        self.text = tk.Text(
            self,
            wrap="word",
            width=1,
            height=1,
            font=("Helvetica Neue", 12),
            bg=USER_BUBBLE,
            fg=USER_TEXT,
            insertbackground=USER_TEXT,
            selectbackground="#FFFFFF",
            selectforeground=USER_BUBBLE,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=3,
            pady=2,
            cursor="xterm",
        )
        self.text.pack(
            fill="both",
            expand=True,
            padx=13,
            pady=9,
        )

        self.configure(width=width, height=height)
        self.pack_propagate(False)

        self.text.insert("1.0", text)
        self._tag_links(text)

        # Keep text selectable but not editable.
        self.text.bind("<Key>", self._block_edit)
        self.text.bind("<Control-c>", self._copy_selection)
        self.text.bind("<Control-C>", self._copy_selection)

        # Context menu.
        self.text.bind("<Button-3>", self._show_context_menu, add="+")
        self.text.bind("<Button-2>", self._show_context_menu, add="+")

    def _block_edit(self, event):
        if event.state & 0x4 and event.keysym.lower() == "c":
            return None
        return "break"

    def _tag_links(self, text: str):
        for index, match in enumerate(URL_PATTERN.finditer(text)):
            raw_url = match.group(0)
            url = raw_url.rstrip(".,;:!?)]}")

            start = match.start()
            end = start + len(url)
            tag = f"url_{index}"

            self.text.tag_add(
                tag,
                f"1.0+{start}c",
                f"1.0+{end}c",
            )
            self.text.tag_configure(
                tag,
                foreground="#DDEBFF",
                underline=True,
            )
            self.text.tag_bind(
                tag,
                "<Enter>",
                lambda _event: self.text.configure(cursor="hand2"),
            )
            self.text.tag_bind(
                tag,
                "<Leave>",
                lambda _event: self.text.configure(cursor="xterm"),
            )
            self.text.tag_bind(
                tag,
                "<Button-1>",
                lambda _event, target=url: self._open_link(target),
            )

            self._url_tags[tag] = url

    def _url_at_event(self, event):
        try:
            index = self.text.index(f"@{event.x},{event.y}")
            tags = self.text.tag_names(index)
        except tk.TclError:
            return None

        for tag in tags:
            if tag in self._url_tags:
                return self._url_tags[tag]

        return None

    def _open_link(self, url: str):
        webbrowser.open_new_tab(url)
        return "break"

    def _copy_selection(self, _event=None):
        try:
            selected = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return "break"

        self.clipboard_clear()
        self.clipboard_append(selected)
        return "break"

    def _select_all(self):
        self.text.tag_add(tk.SEL, "1.0", "end-1c")
        self.text.mark_set(tk.INSERT, "1.0")
        self.text.see(tk.INSERT)

    def _copy_link(self, url: str):
        self.clipboard_clear()
        self.clipboard_append(url)

    def _show_context_menu(self, event):
        menu = tk.Menu(self.text, tearoff=0)

        try:
            self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            has_selection = True
        except tk.TclError:
            has_selection = False

        menu.add_command(
            label="Copy",
            command=self._copy_selection,
            state="normal" if has_selection else "disabled",
        )
        menu.add_command(
            label="Select All",
            command=self._select_all,
        )

        url = self._url_at_event(event)

        if url:
            menu.add_separator()
            menu.add_command(
                label="Open Link",
                command=lambda: self._open_link(url),
            )
            menu.add_command(
                label="Copy Link",
                command=lambda: self._copy_link(url),
            )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

        return "break"


# ----------------------------------------------------------------------
# Application
# ----------------------------------------------------------------------

class ChatGUI(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)

        self.title("CI Nurse")
        self.geometry("980x760")
        self.minsize(760, 580)

        self.client: AgentClient | None = None
        self.busy = False

        self._build_login_view()

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------

    def _clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def _build_login_view(self):
        self._clear_window()

        shell = ctk.CTkFrame(
            self,
            fg_color=BG,
            corner_radius=0,
        )
        shell.pack(fill="both", expand=True)

        form = ctk.CTkFrame(
            shell,
            width=430,
            fg_color=BG,
            corner_radius=0,
        )
        form.place(
            relx=0.5,
            rely=0.46,
            anchor="center",
        )

        title = ctk.CTkLabel(
            form,
            text="CI Nurse",
            text_color=TEXT,
            font=ctk.CTkFont(
                family="Helvetica Neue",
                size=28,
                weight="bold",
            ),
        )
        title.pack(anchor="w", pady=(0, 4))

        subtitle = ctk.CTkLabel(
            form,
            text="Connect to your CI Nurse server",
            text_color=SECONDARY,
            font=ctk.CTkFont(
                family="Helvetica Neue",
                size=13,
            ),
        )
        subtitle.pack(anchor="w", pady=(0, 28))

        ctk.CTkLabel(
            form,
            text="Server",
            text_color=TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.server_var = tk.StringVar(value=DEFAULT_SERVER_URL)

        self.server_entry = ctk.CTkEntry(
            form,
            textvariable=self.server_var,
            width=430,
            height=46,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
            fg_color=CARD,
            text_color=TEXT,
            font=ctk.CTkFont(size=12),
        )
        self.server_entry.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(
            form,
            text="Username",
            text_color=TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.username_var = tk.StringVar()

        self.username_entry = ctk.CTkEntry(
            form,
            textvariable=self.username_var,
            width=430,
            height=46,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
            fg_color=CARD,
            text_color=TEXT,
            font=ctk.CTkFont(size=12),
        )
        self.username_entry.pack(fill="x", pady=(0, 22))
        self.username_entry.bind(
            "<Return>",
            lambda _event: self._start_login(),
        )

        self.login_button = ctk.CTkButton(
            form,
            text="Continue",
            command=self._start_login,
            width=180,
            height=42,
            corner_radius=21,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.login_button.pack(anchor="center")

        self.login_status = ctk.CTkLabel(
            form,
            text="",
            text_color=SECONDARY,
            font=ctk.CTkFont(size=10),
        )
        self.login_status.pack(anchor="center", pady=(12, 0))

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
        self._set_login_busy(True, "Connecting…")

        threading.Thread(
            target=self._login_worker,
            args=(username,),
            daemon=True,
        ).start()

    def _login_worker(self, username: str):
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

    def _ask_to_register(self, username: str):
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

    def _register_worker(self, username: str):
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

    def _on_login_success(self, username: str):
        self.busy = False
        self._build_chat_view(username)

    def _show_login_error(self, message: str):
        self._set_login_busy(
            False,
            "Connection failed",
        )
        messagebox.showerror(
            "Login failed",
            message,
        )

    def _set_login_busy(self, busy: bool, status: str):
        self.busy = busy

        if hasattr(self, "login_button"):
            self.login_button.configure(
                state="disabled" if busy else "normal"
            )

        if hasattr(self, "login_status"):
            self.login_status.configure(text=status)

    # ------------------------------------------------------------------
    # Chat layout
    # ------------------------------------------------------------------

    def _build_chat_view(self, username: str):
        self._clear_window()

        root = ctk.CTkFrame(
            self,
            fg_color=BG,
            corner_radius=0,
        )
        root.pack(fill="both", expand=True)

        # --------------------------------------------------------------
        # Top row
        # --------------------------------------------------------------
        top = ctk.CTkFrame(
            root,
            height=62,
            fg_color=BG,
            corner_radius=0,
        )
        top.pack(fill="x")
        top.pack_propagate(False)

        greeting = ctk.CTkLabel(
            top,
            text=f"Hey, {username}",
            text_color=TEXT,
            font=ctk.CTkFont(
                family="Helvetica Neue",
                size=15,
                weight="bold",
            ),
        )
        greeting.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

        logout_button = ctk.CTkButton(
            top,
            text="Log out",
            command=self._logout,
            width=92,
            height=36,
            corner_radius=18,
            fg_color="#E5E5EA",
            hover_color="#D8D8DD",
            text_color=TEXT,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        logout_button.pack(
            side="right",
            padx=20,
            pady=13,
        )

        # --------------------------------------------------------------
        # Scrollable chat
        # --------------------------------------------------------------
        self.chat_area = ctk.CTkScrollableFrame(
            root,
            fg_color=BG,
            corner_radius=0,
            scrollbar_button_color="#B8B8BD",
            scrollbar_button_hover_color="#99999F",
        )
        self.chat_area.pack(
            fill="both",
            expand=True,
            padx=(14, 10),
            pady=(0, 4),
        )

        self._append_system_message("Conversation ready")

        # --------------------------------------------------------------
        # Composer
        # --------------------------------------------------------------
        composer = ctk.CTkFrame(
            root,
            height=126,
            fg_color=CARD,
            corner_radius=24,
            border_width=1,
            border_color="#E2E2E7",
        )
        composer.pack(
            fill="x",
            padx=22,
            pady=(8, 20),
        )
        composer.pack_propagate(False)

        self.message_box = ctk.CTkTextbox(
            composer,
            height=92,
            corner_radius=0,
            fg_color=CARD,
            text_color=TEXT,
            border_width=0,
            wrap="word",
            font=ctk.CTkFont(
                family="Helvetica Neue",
                size=12,
            ),
        )
        self.message_box.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(16, 8),
            pady=12,
        )

        # Use the underlying Tk Text for precise desktop behavior.
        input_text = self.message_box._textbox

        input_text.bind(
            "<Return>",
            self._on_return,
        )
        input_text.bind(
            "<Shift-Return>",
            self._on_shift_return,
        )
        input_text.bind(
            "<Button-3>",
            self._show_input_context_menu,
            add="+",
        )
        input_text.bind(
            "<Button-2>",
            self._show_input_context_menu,
            add="+",
        )

        controls = ctk.CTkFrame(
            composer,
            fg_color=CARD,
            width=112,
        )
        controls.pack(
            side="right",
            fill="y",
            padx=(4, 14),
            pady=12,
        )

        self.send_button = ctk.CTkButton(
            controls,
            text="Send",
            command=self._send_current_message,
            width=96,
            height=42,
            corner_radius=21,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.send_button.pack(anchor="ne")

        self.status_label = ctk.CTkLabel(
            controls,
            text="",
            text_color=SECONDARY,
            font=ctk.CTkFont(size=9),
        )
        self.status_label.pack(
            anchor="ne",
            pady=(7, 0),
        )

        input_text.focus_set()

    # ------------------------------------------------------------------
    # Message rendering
    # ------------------------------------------------------------------

    def _append_message(
        self,
        sender: str,
        message: str,
        is_user: bool,
    ):
        row = ctk.CTkFrame(
            self.chat_area,
            fg_color="transparent",
            corner_radius=0,
        )
        row.pack(
            fill="x",
            padx=8,
            pady=5,
        )

        if is_user:
            bubble = UserMessageBubble(
                row,
                message,
                max_width=580,
            )
            bubble.pack(
                side="right",
                padx=(120, 4),
            )

            self._bind_wheel_to_outer_chat(bubble.text)

        else:
            # Agent replies use the dedicated Markdown renderer.
            wrapper = ctk.CTkFrame(
                row,
                fg_color=CARD,
                corner_radius=18,
                border_width=0,
            )
            wrapper.pack(
                side="left",
                fill="x",
                expand=True,
                padx=(4, 90),
            )

            markdown_height = estimate_markdown_height(message)

            markdown = CTkMarkdown(
                wrapper,
                height=markdown_height,
                fg_color=CARD,
                text_color=TEXT,
                border_width=0,
                corner_radius=16,
                font=("Helvetica Neue", 12),
            )
            markdown.pack(
                fill="x",
                expand=True,
                padx=6,
                pady=4,
            )

            markdown.set_markdown(message)

            # Add normal desktop right-click behavior to CTkMarkdown's
            # underlying Tk Text widget.
            markdown_text = markdown._textbox
            markdown_text.bind(
                "<Button-3>",
                lambda event, widget=markdown_text:
                    self._show_readonly_context_menu(event, widget),
                add="+",
            )
            markdown_text.bind(
                "<Button-2>",
                lambda event, widget=markdown_text:
                    self._show_readonly_context_menu(event, widget),
                add="+",
            )

            self._bind_wheel_to_outer_chat(markdown_text)

        self.after(
            10,
            self._scroll_chat_to_bottom,
        )

    def _append_system_message(self, message: str):
        label = ctk.CTkLabel(
            self.chat_area,
            text=message,
            text_color=SYSTEM_TEXT,
            fg_color="transparent",
            font=ctk.CTkFont(size=9),
            justify="center",
            wraplength=640,
        )
        label.pack(
            fill="x",
            padx=40,
            pady=10,
        )

        self.after(
            10,
            self._scroll_chat_to_bottom,
        )

    # ------------------------------------------------------------------
    # Scrolling
    # ------------------------------------------------------------------

    def _scroll_chat_to_bottom(self):
        try:
            self.chat_area._parent_canvas.update_idletasks()
            self.chat_area._parent_canvas.yview_moveto(1.0)
        except (AttributeError, tk.TclError):
            pass

    def _bind_wheel_to_outer_chat(self, widget):
        """
        Text widgets normally consume wheel events.
        Forward them to the outer chat so mouse/trackpad scrolling feels
        consistent anywhere over a message.
        """
        widget.bind(
            "<MouseWheel>",
            self._forward_mousewheel,
            add="+",
        )
        widget.bind(
            "<Button-4>",
            self._forward_linux_scroll_up,
            add="+",
        )
        widget.bind(
            "<Button-5>",
            self._forward_linux_scroll_down,
            add="+",
        )

    def _forward_mousewheel(self, event):
        try:
            canvas = self.chat_area._parent_canvas

            delta = event.delta
            if delta == 0:
                return "break"

            if abs(delta) < 120:
                units = -1 if delta > 0 else 1
            else:
                units = int(-delta / 120)

            canvas.yview_scroll(units * 3, "units")
        except (AttributeError, tk.TclError):
            pass

        return "break"

    def _forward_linux_scroll_up(self, _event):
        try:
            self.chat_area._parent_canvas.yview_scroll(-3, "units")
        except (AttributeError, tk.TclError):
            pass
        return "break"

    def _forward_linux_scroll_down(self, _event):
        try:
            self.chat_area._parent_canvas.yview_scroll(3, "units")
        except (AttributeError, tk.TclError):
            pass
        return "break"

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def _show_readonly_context_menu(self, event, widget):
        menu = tk.Menu(widget, tearoff=0)

        try:
            widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            has_selection = True
        except tk.TclError:
            has_selection = False

        menu.add_command(
            label="Copy",
            command=lambda: self._copy_from_widget(widget),
            state="normal" if has_selection else "disabled",
        )
        menu.add_command(
            label="Select All",
            command=lambda: self._select_all_widget(widget),
        )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

        return "break"

    def _copy_from_widget(self, widget):
        try:
            selected = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return

        self.clipboard_clear()
        self.clipboard_append(selected)

    @staticmethod
    def _select_all_widget(widget):
        widget.tag_add(tk.SEL, "1.0", "end-1c")
        widget.mark_set(tk.INSERT, "1.0")
        widget.see(tk.INSERT)

    def _show_input_context_menu(self, event):
        widget = self.message_box._textbox
        menu = tk.Menu(widget, tearoff=0)

        try:
            widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            has_selection = True
        except tk.TclError:
            has_selection = False

        menu.add_command(
            label="Cut",
            command=lambda: widget.event_generate("<<Cut>>"),
            state="normal" if has_selection else "disabled",
        )
        menu.add_command(
            label="Copy",
            command=lambda: widget.event_generate("<<Copy>>"),
            state="normal" if has_selection else "disabled",
        )
        menu.add_command(
            label="Paste",
            command=lambda: widget.event_generate("<<Paste>>"),
        )

        menu.add_separator()

        menu.add_command(
            label="Select All",
            command=lambda: self._select_all_widget(widget),
        )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

        return "break"

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _on_return(self, _event):
        # While waiting for a reply, Enter becomes a newline so the user
        # can continue composing the next message.
        if self.busy:
            self.message_box.insert("insert", "\n")
            return "break"

        self._send_current_message()
        return "break"

    def _on_shift_return(self, _event):
        self.message_box.insert("insert", "\n")
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

    def _send_worker(self, message: str):
        try:
            data = self.client.send_message(message)
            output = data.get("output")

            if output is None:
                output = "The server returned no 'output' field."

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

    def _on_agent_response(self, output: str):
        self._append_message(
            "CI Nurse",
            output,
            False,
        )

        self._set_chat_busy(False)
        self.message_box._textbox.focus_set()

    def _on_send_error(self, message: str):
        self._append_system_message(
            f"Error: {message}"
        )

        self._set_chat_busy(False)

        messagebox.showerror(
            "Message failed",
            message,
        )

    def _set_chat_busy(self, busy: bool):
        self.busy = busy

        if hasattr(self, "send_button"):
            self.send_button.configure(
                state="disabled" if busy else "normal"
            )

        # Input deliberately stays editable while the agent is responding.
        if hasattr(self, "message_box"):
            self.message_box.configure(state="normal")

        if hasattr(self, "status_label"):
            self.status_label.configure(
                text="Thinking…" if busy else ""
            )

    # ------------------------------------------------------------------
    # Logout + errors
    # ------------------------------------------------------------------

    def _logout(self):
        if self.client:
            self.client.logout()

        self.client = None
        self.busy = False

        self._build_login_view()

    @staticmethod
    def _request_error(exc: requests.RequestException) -> str:
        response = getattr(exc, "response", None)

        if response is not None:
            try:
                detail = response.json().get("detail")

                if detail:
                    return f"{response.status_code}: {detail}"

            except (ValueError, AttributeError):
                pass

            body = response.text.strip()

            if body:
                return f"{response.status_code}: {body}"

        return str(exc)


if __name__ == "__main__":
    app = ChatGUI()
    app.mainloop()
