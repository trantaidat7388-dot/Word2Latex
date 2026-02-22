# Word2LaTeX Research Project

Advanced Word document (.docx) to LaTeX conversion system with comprehensive formula support.

## 🚀 Quick Start

### Option 1: Web Application (Recommended)

1. **Start Backend API:**
   ```bash
   # Activate virtual environment
   .venv\Scripts\Activate.ps1
   
   # Install backend dependencies
   pip install -r backend/requirements.txt
   
   # Run FastAPI server
   cd backend
   python main.py
   ```
   Backend runs at: http://localhost:8000

2. **Start Frontend:**
   ```bash
   # In new terminal
   cd frontend
   npm install
   npm run dev
   ```
   Frontend runs at: http://localhost:3000

3. **Configure Firebase** (see [HUONG_DAN_FIREBASE.md](HUONG_DAN_FIREBASE.md))

### Option 2: Command Line

```bash
python src/chuyen_doi.py
```

---

## Features

- 📄 **Complete Document Conversion**: Convert Word documents to LaTeX with full structure preservation
- 🧮 **Dual Formula Support**: 
  - OMML (Office Math Markup Language) with 3-tier processing pipeline
  - OLE Equation 3.0 with custom MTEF binary parser
- 🖼️ **Smart Image Processing**: Automatic quality analysis and decorative image filtering
- 📊 **Table Support**: Complex tables with merged cells
- 📝 **Style Mapping**: Automatic Word styles to LaTeX commands conversion
- 🎯 **Vietnamese Support**: Full Vietnamese text processing with XeLaTeX
- 🌐 **Web Interface**: React frontend with Firebase authentication
- ⚡ **REST API**: FastAPI backend for programmatic access

## Architecture

### Backend (Python)
The conversion engine consists of 6 modular components:

- **chuyen_doi.py**: Main controller orchestrating the conversion process
- **xu_ly_toan.py**: OMML mathematics processing (XSLT → Pandoc → Manual parsing)
- **xu_ly_ole_equation.py**: OLE Equation 3.0 MTEF binary parser and converter 
- **xu_ly_anh.py**: Image analysis and quality scoring system
- **config.py**: Configuration, namespaces, and character mappings
- **utils.py**: LaTeX utilities and XeLaTeX compilation

### Frontend (React)
Modern web interface with:
- **React 18 + Vite**: Fast development and optimized production builds
- **Tailwind CSS**: Glassmorphism UI design
- **Firebase**: Authentication (Google + Email) and Firestore database
- **Framer Motion**: Smooth animations and transitions
- **react-dropzone**: Drag & drop file upload

### API (FastAPI)
RESTful API endpoints:
- `POST /api/chuyen-doi`: Upload and convert .docx files
- `GET /api/tai-ve/{filename}`: Download converted .tex files
- `GET /api/trang-thai/{job_id}`: Check conversion status

## Project Structure

```
Word2Latex_Research/
├── src/                    # Python conversion engine
│   ├── chuyen_doi.py      # Main controller
│   ├── xu_ly_toan.py      # Math processing
│   ├── xu_ly_ole_equation.py
│   ├── xu_ly_anh.py       # Image processing
│   ├── config.py
│   └── utils.py
├── backend/               # FastAPI server
│   ├── main.py           # API endpoints
│   ├── requirements.txt
│   ├── uploads/          # Temporary uploads
│   └── outputs/          # Converted files
├── frontend/             # React application
│   ├── src/
│   │   ├── features/     # Auth, Conversion, History
│   │   ├── components/   # Shared UI components
│   │   └── services/     # Firebase & API
│   ├── package.json
│   └── vite.config.js
├── input_data/           # LaTeX templates
└── output/              # CLI output directory
```

## Installation

### Python Backend
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### React Frontend
```bash
cd frontend
npm install
```

## Usage

### Web Application
See [Quick Start](#-quick-start) above.

### Command Line
```bash
# Place your .docx file in input_data/
python src/chuyen_doi.py

# Output in output/ directory
```

### API Documentation
Visit http://localhost:8000/docs for interactive Swagger UI.

## Requirements

- Python 3.8+
- python-docx==1.1.0
- lxml>=4.9.0  
- Pillow==10.2.0
- olefile (for OLE Equation processing)
- XeLaTeX (for PDF compilation)

## Formula Processing Capabilities

### OMML Processing Pipeline
1. **XSLT Transformation**: OMML → MathML → LaTeX (most accurate)
2. **Pandoc Fallback**: Subprocess conversion for complex cases  
3. **Manual Parser**: Recursive XML parsing as final fallback

### OLE Equation 3.0 Support
- Full MTEF v3 binary format parser
- Template processing: fractions, roots, integrals, matrices, fences
- 100+ Unicode symbol mappings
- Handles legacy Equation Editor content

### Before/After Examples

**Before (Image-based)**:
```latex
\includegraphics[height=1.5em]{images/formula_3.png}
```

**After (Native LaTeX)**:
```latex
f(x)=\int_{a}^{b} \sqrt[k]{5x-9}\, dx

\boldsymbol{T}=\begin{bmatrix} 
1 & 0 & 255 \\ 
0 & 1 & 0 \\ 
0 & 0 & 1 
\end{bmatrix}
```

## Image Processing Features

Advanced scoring system (0.0-1.0):
- **Entropy Analysis** (30%): Information complexity measurement
- **Color Variance** (25%): Color diversity assessment  
- **Edge Detection** (20%): Sobel filter-based edge density
- **Size Scoring** (15%): Optimal dimension preferences
- **Histogram Analysis** (10%): Monotone image detection

Score ≥ 0.7: Content image (keep) | Score < 0.7: Decorative (filter out)

## Documentation

See detailed guides:
- **[DOCUMENTATION.txt](DOCUMENTATION.txt)**: Comprehensive technical documentation
- **[HUONG_DAN_FIREBASE.md](HUONG_DAN_FIREBASE.md)**: Firebase setup guide (Vietnamese)
- **[HUONG_DAN_BACKEND.md](HUONG_DAN_BACKEND.md)**: Backend API guide (Vietnamese)

Technical details include:
- Detailed architecture overview
- Data flow diagrams  
- MTEF specification details
- Performance metrics
- Extension guidelines

## API Endpoints

### POST /api/chuyen-doi
Upload and convert Word document to LaTeX.

**Request:**
- `file`: .docx file (max 10MB)
- `template_type`: "onecolumn" or "twocolumn"

**Response:**
```json
{
  "trang_thai": "thanh_cong",
  "job_id": "uuid",
  "ten_file_dau_ra": "document_20260222_143022.tex",
  "duong_dan_tai_ve": "/api/tai-ve/document_20260222_143022.tex"
}
```

### GET /api/tai-ve/{filename}
Download converted .tex file.

### GET /api/trang-thai/{job_id}
Check conversion job status.

## License

MIT License - feel free to use and modify for your research needs.

## Contributing

Contributions welcome! The modular architecture makes it easy to:
- Add new math processors
- Extend image filtering algorithms  
- Implement additional Word features
- Improve style mappings

## Version History

- **v2.0**: Added OLE Equation 3.0 MTEF parser support
- **v1.0**: Initial OMML processing with image fallback