# Word2LaTeX Research Project

Advanced Word document (.docx) to LaTeX conversion system with comprehensive formula support.

## Features

- 📄 **Complete Document Conversion**: Convert Word documents to LaTeX with full structure preservation
- 🧮 **Dual Formula Support**: 
  - OMML (Office Math Markup Language) with 3-tier processing pipeline
  - OLE Equation 3.0 with custom MTEF binary parser
- 🖼️ **Smart Image Processing**: Automatic quality analysis and decorative image filtering
- 📊 **Table Support**: Complex tables with merged cells
- 📝 **Style Mapping**: Automatic Word styles to LaTeX commands conversion
- 🎯 **Vietnamese Support**: Full Vietnamese text processing with XeLaTeX

## Architecture

The system consists of 6 modular components:

- **chuyen_doi.py**: Main controller orchestrating the conversion process
- **xu_ly_toan.py**: OMML mathematics processing (XSLT → Pandoc → Manual parsing)
- **xu_ly_ole_equation.py**: OLE Equation 3.0 MTEF binary parser and converter 
- **xu_ly_anh.py**: Image analysis and quality scoring system
- **config.py**: Configuration, namespaces, and character mappings
- **utils.py**: LaTeX utilities and XeLaTeX compilation

## Installation

```bash
# Clone repository
git clone https://github.com/trantaidat7388-dot/Word2Latex.git
cd Word2Latex

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Place your .docx file in input_data/ directory
# Run conversion
python src/chuyen_doi.py

# Output will be generated in output/ directory
# Automatic XeLaTeX compilation creates PDF
```

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

See [DOCUMENTATION.txt](DOCUMENTATION.txt) for comprehensive technical documentation including:
- Detailed architecture overview
- Data flow diagrams  
- MTEF specification details
- Performance metrics
- Extension guidelines

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