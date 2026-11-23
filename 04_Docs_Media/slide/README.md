# Template LaTeX Beamer HCMUT

Template gồm bìa, mục lục và thành viên, ba chương mẫu (nội dung, công thức,
bảng), trang chia chương và trang kết thúc. Thay các placeholder `[...]`
bằng thông tin bài mới. Theme Madrid, tỉ lệ 16:9, màu, font, header/footer,
logo và hai file nền trong `images/` giữ nguyên.

## Cài đặt và build

- Cài MiKTeX hoặc TeX Live, có `latexmk`, Beamer, `babel` tiếng Việt,
  VNTeX, TikZ và `listings`. Trên Windows, `latexmk` cần Perl
  (có thể dùng Strawberry Perl). Đảm bảo các lệnh nằm trong `PATH`.
- Cài extension **LaTeX Workshop** (`James-Yu.latex-workshop`) trong VS Code
  và mở **cả thư mục project**.
- Compiler đang dùng: **pdfLaTeX qua latexmk**. Cấu hình `.vscode/settings.json`
  tự build khi lưu file `.tex` (`onSave`). File chính là `main.tex`,
  kể cả khi sửa file trong `chapters/`.
- Build thủ công: **Ctrl+Alt+B**. Xem PDF: **Ctrl+Alt+V** hoặc Command Palette
  → **LaTeX Workshop: View LaTeX PDF file**.

Build bằng terminal từ thư mục project:

```powershell
latexmk -pdf -synctex=1 -interaction=nonstopmode -file-line-error -halt-on-error main.tex
```

Kết quả là `main.pdf`. PDF đầu ra và file build phụ được bỏ qua bởi Git;
PDF nền trong `images/` và cấu hình `.vscode/` vẫn được giữ.

## Sửa bài thuyết trình

- **Thông tin bìa:** sửa `\title` (tên ngắn và tên đầy đủ), `\subtitle`,
  `\author` (tên ngắn ở footer và nội dung đầy đủ), `\date` trong `main.tex`.
  Sửa bảng thành viên, mô tả mục lục và dòng đơn vị ở trang kết thúc tại cùng file.
- **Nội dung:** sửa `chapters/chapter01.tex` đến `chapter03.tex`.
  Công thức `y = ax + b` chỉ minh họa cú pháp, không phải kết quả nghiên cứu.
- **Thêm slide:** chèn vào file chương:

```latex
\begin{frame}{[Tiêu đề slide]}
  [Nội dung slide.]
\end{frame}
```

- **Thêm chương:** sao chép một file chương thành `chapters/chapter04.tex`,
  sửa `\section` và `\ChapterDivider`, thêm `\input{chapters/chapter04}`
  trong `main.tex` trước trang kết thúc. Cập nhật slide mục lục tương ứng.
- **Ảnh:** thêm ảnh vào `images/` và dùng `\includegraphics`.
  Giữ `Background.pdf` và `FrontBackground.pdf` để bảo toàn thiết kế.
- Slide chứa `lstlisting` cần `\begin{frame}[fragile]{...}`.

Giữ pdfLaTeX để dùng ngay với cấu hình hiện tại. Nếu chủ động chuyển sang
XeLaTeX/LuaLaTeX, cần cài Noto Sans và Noto Sans Mono theo cấu hình font.
