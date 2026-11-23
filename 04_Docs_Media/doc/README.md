# Template báo cáo HCMUT

Template tối giản cho báo cáo môn học và đồ án, giữ định dạng của dự án gốc:
trang bìa, font, lề, giãn dòng, heading, số trang và định dạng code.
Class đang dùng là `hcmut-report` (nhãn tiếng Anh), hỗ trợ nội dung tiếng Việt.
Không cần sửa các file `.cls` và `.sty` để viết báo cáo.

## Cấu trúc

```text
.
├── .vscode/settings.json       # Cấu hình LaTeX Workshop
├── chapters/
│   ├── chapter1.tex            # Giới thiệu
│   ├── chapter2.tex            # Công thức, bảng, hình, code, tham chiếu
│   └── chapter3.tex            # Kết luận và trích dẫn
├── graphics/hcmut.png          # Logo dùng cho bìa/header và ví dụ
├── refs/references.tex         # Tài liệu tham khảo mẫu
├── .gitignore
├── build.ps1
├── codespace.sty
├── hcmut-report.cls
├── hcmut-report-vi.cls         # Class thay thế được giữ từ dự án gốc
├── README.md
└── report.tex                 # File chính
```

## Chỉnh sửa báo cáo

Sửa vùng **THONG TIN BAO CAO** ở đầu `report.tex`: khoa, môn học, loại báo cáo,
đề tài, giảng viên, sinh viên và MSSV. Giữ các dấu `&` trong `\advisor` và
`\stuname` để căn cột; thêm sinh viên bằng dòng `& Họ tên & MSSV \\`.
Tháng và năm mặc định theo ngày biên dịch; dùng `\reporttime{...}` để đặt thủ công.

Viết nội dung trong `chapters/`. Class gốc dựa trên `article`, nên mỗi chương
dùng `\section`, mục dùng `\subsection`, mục nhỏ dùng `\subsubsection`.
Để thêm chương, tạo file rồi thêm `\clearpage` và
`\input{chapters/chapter4.tex}` trong `report.tex`, trước tài liệu tham khảo.
Để xóa chương, bỏ dòng `\input` tương ứng và xóa file; cập nhật các tham chiếu liên quan.

## Thêm nội dung

- **Hình:** đặt file trong `graphics/`, dùng môi trường `figure` với
  `\includegraphics[width=0.8\textwidth]{graphics/ten-hinh.png}` và `\caption{...}`.
  Giữ `hcmut.png` vì trang bìa và header phụ thuộc vào logo này.
- **Bảng:** dùng `table` chứa `tabular`; xem ví dụ trong `chapter2.tex`.
- **Công thức:** dùng `$...$` trong dòng hoặc môi trường `equation` để đánh số.
- **Code:** dùng `lstlisting`, đặt `language`, `caption` và `label` như ví dụ.
  Ví dụ dùng ASCII trong code để tương thích cấu hình hiện tại.
- **Tham chiếu:** đặt `\label{...}` sau `\caption` hoặc trong `equation`,
  sau đó gọi `\ref{...}` trong nội dung.
- **Tài liệu tham khảo:** thêm `\bibitem{khoa}` vào `refs/references.tex`,
  rồi trích dẫn bằng `\cite{khoa}`. Dùng `thebibliography` có sẵn,
  không cần file `.bib` hoặc bước BibTeX riêng.

Mục lục và danh sách hình, bảng, đoạn mã được cập nhật tự động khi build đủ lượt.

## Biên dịch

Cài MiKTeX hoặc TeX Live có pdfLaTeX và các gói dự án sử dụng (gồm hỗ trợ
tiếng Việt VnTeX). Thêm `pdflatex` vào `PATH` khi dùng VS Code.

- **VS Code:** cài extension LaTeX Workshop, mở thư mục dự án và `report.tex`,
  chọn **Build LaTeX project** với recipe **pdfLaTeX**. Cấu hình cũng build khi lưu.
- **PowerShell:** chạy từ thư mục dự án:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\build.ps1
  ```

Script giữ workflow pdfLaTeX ba lượt, tìm trình biên dịch trong `PATH` hoặc
đường dẫn MiKTeX mặc định của người dùng. Kết quả là `report.pdf` ở thư mục gốc.
File phụ khi biên dịch và PDF đầu ra được bỏ qua bởi `.gitignore`.
