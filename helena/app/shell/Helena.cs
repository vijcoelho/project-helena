// The Helena window: a frameless WebView2 window, so the page draws its own title bar and buttons.
// Built on first launch by app/shell.js with the csc that ships with Windows (.NET Framework 4); no SDK, no Electron.
//   Helena.exe <url>
//   Helena.exe          (the Start menu shortcut) the running Helena server, or one it starts hidden
// The page talks to it with chrome.webview.postMessage: "min", "max", "close", "drag" (from the title bar), "pick" (or "pick:en").
// It answers "max:1" / "max:0" so the page can switch the maximize glyph, and "folder:<path>" ("folder:" if cancelled).
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        string url = args.Length > 0 ? args[0] : Server();
        if (url == null) { MessageBox.Show("A Helena não conseguiu subir. Abra uma vez com /helena:app no Claude Code.\n\nHelena could not start. Open it once with /helena:app in Claude Code.", "Helena"); return; }
        Application.Run(new Window(url));
    }

    // no address: the server already running (~/.helena/app.port), or this plugin version's server started now, with no
    // console. launch.txt (node, then server.js) is written by app/shell.js next to this exe, in ~/.helena/app-shell.
    static string Server()
    {
        string dir = Path.GetDirectoryName(Application.ExecutablePath);
        try
        {
            string url = "http://127.0.0.1:" + File.ReadAllText(Path.Combine(dir, "..", "app.port")).Trim() + "/";
            var r = WebRequest.Create(url + "api/state");
            r.Timeout = 1500;
            using (r.GetResponse()) return url;
        }
        catch { }
        try
        {
            string[] run = File.ReadAllLines(Path.Combine(dir, "launch.txt"));
            var p = Process.Start(new ProcessStartInfo(run[0], "\"" + run[1] + "\" --serve --no-open --here \"\"")
            {
                UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true,
                WorkingDirectory = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            });
            string line = p.StandardOutput.ReadLine();  // the server prints its address once it listens, and nothing after
            return line != null && line.StartsWith("http") ? line : null;
        }
        catch { return null; }
    }
}

class Window : Form
{
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);
    [DllImport("user32.dll")] static extern bool ReleaseCapture();
    [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr hwnd, int msg, IntPtr w, IntPtr l);

    const int WM_NCHITTEST = 0x84, WM_NCLBUTTONDOWN = 0xA1, HTCAPTION = 2;
    const int GRIP = 6;  // the edge you can resize from: the page sits inside it, on the same black
    readonly WebView2 web = new WebView2();
    readonly string url;

    public Window(string url)
    {
        this.url = url;
        Text = "Helena";
        FormBorderStyle = FormBorderStyle.None;
        BackColor = Color.Black;
        Width = 1320; Height = 880;
        MinimumSize = new Size(420, 480);
        StartPosition = FormStartPosition.CenterScreen;
        Padding = new Padding(GRIP);
        try
        {
            string ico = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "helena.ico");
            if (File.Exists(ico)) Icon = new Icon(ico);
        }
        catch { }
        web.Dock = DockStyle.Fill;
        web.DefaultBackgroundColor = Color.Black;
        Controls.Add(web);
        HandleCreated += delegate
        {
            int on = 1, round = 2;
            DwmSetWindowAttribute(Handle, 20, ref on, sizeof(int));     // dark mode
            DwmSetWindowAttribute(Handle, 33, ref round, sizeof(int));  // Windows 11 rounded corners
        };
        Resize += delegate
        {
            Padding = new Padding(WindowState == FormWindowState.Maximized ? 0 : GRIP);
            if (web.CoreWebView2 != null) web.CoreWebView2.PostWebMessageAsString(WindowState == FormWindowState.Maximized ? "max:1" : "max:0");
        };
        Load += async delegate
        {
            var env = await CoreWebView2Environment.CreateAsync(null,
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Helena", "webview"), null);
            await web.EnsureCoreWebView2Async(env);
            web.CoreWebView2.Settings.IsStatusBarEnabled = false;
            web.CoreWebView2.NewWindowRequested += delegate (object s, CoreWebView2NewWindowRequestedEventArgs e)
            {
                e.Handled = true;  // a link opens in the real browser, not in here
                try { Process.Start(new ProcessStartInfo(e.Uri) { UseShellExecute = true }); } catch { }
            };
            web.CoreWebView2.WebMessageReceived += OnMessage;
            web.CoreWebView2.Navigate(url);
        };
    }

    // a drop shadow, like any other window
    protected override CreateParams CreateParams
    {
        get { var p = base.CreateParams; p.ClassStyle |= 0x20000; return p; }
    }

    void OnMessage(object s, CoreWebView2WebMessageReceivedEventArgs e)
    {
        string m;
        try { m = e.TryGetWebMessageAsString(); } catch { return; }
        if (m == "min") WindowState = FormWindowState.Minimized;
        else if (m == "max") ToggleMax();
        else if (m == "close") Close();
        else if (m.StartsWith("pick"))
        {
            // ponytail: .NET 4's tree dialog; the Explorer-style one (IFileOpenDialog, FOS_PICKFOLDERS) is COM interop
            using (var d = new FolderBrowserDialog { Description = m == "pick:en" ? "Where the AI works" : "Onde a IA trabalha", ShowNewFolderButton = true })
                web.CoreWebView2.PostWebMessageAsString("folder:" + (d.ShowDialog(this) == DialogResult.OK ? d.SelectedPath : ""));
        }
        else if (m == "drag")
        {
            // hand the drag to Windows: it moves the window and snaps it to the screen edges
            ReleaseCapture();
            SendMessage(Handle, WM_NCLBUTTONDOWN, (IntPtr)HTCAPTION, IntPtr.Zero);
        }
    }

    void ToggleMax()
    {
        if (WindowState == FormWindowState.Maximized) { WindowState = FormWindowState.Normal; return; }
        MaximizedBounds = Screen.FromHandle(Handle).WorkingArea;  // not over the taskbar
        WindowState = FormWindowState.Maximized;
    }

    // the GRIP-wide edge around the page resizes the window
    protected override void WndProc(ref Message m)
    {
        base.WndProc(ref m);
        if (m.Msg != WM_NCHITTEST || WindowState == FormWindowState.Maximized) return;
        var p = PointToClient(new Point(m.LParam.ToInt32() & 0xffff, m.LParam.ToInt32() >> 16));
        bool l = p.X < GRIP, r = p.X >= ClientSize.Width - GRIP, t = p.Y < GRIP, b = p.Y >= ClientSize.Height - GRIP;
        int hit = t && l ? 13 : t && r ? 14 : b && l ? 16 : b && r ? 17 : l ? 10 : r ? 11 : t ? 12 : b ? 15 : 0;
        if (hit != 0) m.Result = (IntPtr)hit;
    }
}
