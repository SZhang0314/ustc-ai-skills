# 用 WPS Office（Kingsoft）COM 自动化把 PPTX 转成 PDF。
# 适用场景：系统无 PowerPoint / LibreOffice 时，用 WPS 渲染幻灯片（保留矢量图形）。
# 用法: python wps_ppt2pdf.py <src.pptx> <dst.pdf>
# 依赖: pip install pywin32；已安装 WPS Office（注册表 App Paths\powerpnt.exe 指向 wps.exe）
import sys, os
import win32com.client as win32

src = os.path.abspath(sys.argv[1])
dst = os.path.abspath(sys.argv[2])
app = win32.Dispatch("Kwpp.Application")
# 注意：app.Visible = False 在 WPS 下会抛 com_error，必须跳过（不要设置）
try:
    app.Visible = False
except Exception:
    pass
pres = app.Presentations.Open(src)
pres.SaveAs(dst, 32)   # 32 = ppSaveAsPDF
pres.Close()
app.Quit()
print("OK", dst)
