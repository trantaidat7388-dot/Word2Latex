<?xml version="1.0" encoding="UTF-8"?>
<!--
  OMML2MML.XSL - Simplified OMML to MathML transform.
  Based on the Microsoft Office OMML2MML stylesheet structure.
  This is a minimal community version for use when the Office XSL is unavailable.
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
  xmlns:mml="http://www.w3.org/1998/Math/MathML"
  exclude-result-prefixes="m">

  <xsl:output method="xml" indent="yes" encoding="UTF-8"/>

  <!-- ROOT: match oMath -->
  <xsl:template match="m:oMath">
    <math xmlns="http://www.w3.org/1998/Math/MathML">
      <mrow>
        <xsl:apply-templates/>
      </mrow>
    </math>
  </xsl:template>

  <!-- m:oMathPara -->
  <xsl:template match="m:oMathPara">
    <xsl:apply-templates/>
  </xsl:template>

  <!-- m:r  (run – contains m:t text) -->
  <xsl:template match="m:r">
    <xsl:apply-templates select="m:t"/>
  </xsl:template>

  <!-- m:t  (text) -->
  <xsl:template match="m:t">
    <xsl:variable name="txt" select="normalize-space(.)"/>
    <xsl:choose>
      <xsl:when test="string-length($txt) = 1 and translate($txt, '0123456789', '') = ''">
        <mn xmlns="http://www.w3.org/1998/Math/MathML"><xsl:value-of select="$txt"/></mn>
      </xsl:when>
      <xsl:when test="translate($txt, '0123456789.', '') = ''">
        <mn xmlns="http://www.w3.org/1998/Math/MathML"><xsl:value-of select="$txt"/></mn>
      </xsl:when>
      <xsl:when test="translate($txt, '+-=&lt;&gt;()[]{}|/\!@#$%^&amp;*~`,;:?', '') = ''">
        <mo xmlns="http://www.w3.org/1998/Math/MathML"><xsl:value-of select="$txt"/></mo>
      </xsl:when>
      <xsl:when test="string-length($txt) = 1">
        <mi xmlns="http://www.w3.org/1998/Math/MathML"><xsl:value-of select="$txt"/></mi>
      </xsl:when>
      <xsl:otherwise>
        <mi xmlns="http://www.w3.org/1998/Math/MathML"><xsl:value-of select="$txt"/></mi>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- m:f  (fraction) -->
  <xsl:template match="m:f">
    <mfrac xmlns="http://www.w3.org/1998/Math/MathML">
      <mrow><xsl:apply-templates select="m:num"/></mrow>
      <mrow><xsl:apply-templates select="m:den"/></mrow>
    </mfrac>
  </xsl:template>

  <xsl:template match="m:num|m:den">
    <xsl:apply-templates/>
  </xsl:template>

  <!-- m:rad  (radical / square root) -->
  <xsl:template match="m:rad">
    <xsl:variable name="degText" select="normalize-space(m:deg)"/>
    <xsl:choose>
      <xsl:when test="$degText != '' and $degText != '2'">
        <mroot xmlns="http://www.w3.org/1998/Math/MathML">
          <mrow><xsl:apply-templates select="m:e"/></mrow>
          <mrow><xsl:apply-templates select="m:deg"/></mrow>
        </mroot>
      </xsl:when>
      <xsl:otherwise>
        <msqrt xmlns="http://www.w3.org/1998/Math/MathML">
          <mrow><xsl:apply-templates select="m:e"/></mrow>
        </msqrt>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- m:sSub  (subscript) -->
  <xsl:template match="m:sSub">
    <msub xmlns="http://www.w3.org/1998/Math/MathML">
      <mrow><xsl:apply-templates select="m:e"/></mrow>
      <mrow><xsl:apply-templates select="m:sub"/></mrow>
    </msub>
  </xsl:template>

  <!-- m:sSup  (superscript) -->
  <xsl:template match="m:sSup">
    <msup xmlns="http://www.w3.org/1998/Math/MathML">
      <mrow><xsl:apply-templates select="m:e"/></mrow>
      <mrow><xsl:apply-templates select="m:sup"/></mrow>
    </msup>
  </xsl:template>

  <!-- m:sSubSup  (sub + superscript) -->
  <xsl:template match="m:sSubSup">
    <msubsup xmlns="http://www.w3.org/1998/Math/MathML">
      <mrow><xsl:apply-templates select="m:e"/></mrow>
      <mrow><xsl:apply-templates select="m:sub"/></mrow>
      <mrow><xsl:apply-templates select="m:sup"/></mrow>
    </msubsup>
  </xsl:template>

  <!-- m:nary  (sum, integral, product, ...) -->
  <xsl:template match="m:nary">
    <mrow xmlns="http://www.w3.org/1998/Math/MathML">
      <munderover>
        <mo>
          <xsl:choose>
            <xsl:when test="m:naryPr/m:chr/@m:val"><xsl:value-of select="m:naryPr/m:chr/@m:val"/></xsl:when>
            <xsl:otherwise>&#x2211;</xsl:otherwise> <!-- default ∑ -->
          </xsl:choose>
        </mo>
        <mrow><xsl:apply-templates select="m:sub"/></mrow>
        <mrow><xsl:apply-templates select="m:sup"/></mrow>
      </munderover>
      <mrow><xsl:apply-templates select="m:e"/></mrow>
    </mrow>
  </xsl:template>

  <!-- m:d  (delimiters / parentheses) -->
  <xsl:template match="m:d">
    <mfenced xmlns="http://www.w3.org/1998/Math/MathML">
      <xsl:if test="m:dPr/m:begChr/@m:val">
        <xsl:attribute name="open"><xsl:value-of select="m:dPr/m:begChr/@m:val"/></xsl:attribute>
      </xsl:if>
      <xsl:if test="m:dPr/m:endChr/@m:val">
        <xsl:attribute name="close"><xsl:value-of select="m:dPr/m:endChr/@m:val"/></xsl:attribute>
      </xsl:if>
      <xsl:for-each select="m:e">
        <mrow><xsl:apply-templates/></mrow>
      </xsl:for-each>
    </mfenced>
  </xsl:template>

  <!-- m:func  (named function: sin, cos, log, ...) -->
  <xsl:template match="m:func">
    <mrow xmlns="http://www.w3.org/1998/Math/MathML">
      <mo><xsl:value-of select="normalize-space(m:fName)"/></mo>
      <mrow><xsl:apply-templates select="m:e"/></mrow>
    </mrow>
  </xsl:template>

  <!-- m:limLow  (lower limit) -->
  <xsl:template match="m:limLow">
    <munder xmlns="http://www.w3.org/1998/Math/MathML">
      <mrow><xsl:apply-templates select="m:e"/></mrow>
      <mrow><xsl:apply-templates select="m:lim"/></mrow>
    </munder>
  </xsl:template>

  <!-- m:limUpp  (upper limit) -->
  <xsl:template match="m:limUpp">
    <mover xmlns="http://www.w3.org/1998/Math/MathML">
      <mrow><xsl:apply-templates select="m:e"/></mrow>
      <mrow><xsl:apply-templates select="m:lim"/></mrow>
    </mover>
  </xsl:template>

  <!-- m:acc  (accent: hat, tilde, bar, ...) -->
  <xsl:template match="m:acc">
    <mover xmlns="http://www.w3.org/1998/Math/MathML" accent="true">
      <mrow><xsl:apply-templates select="m:e"/></mrow>
      <mo>
        <xsl:choose>
          <xsl:when test="m:accPr/m:chr/@m:val"><xsl:value-of select="m:accPr/m:chr/@m:val"/></xsl:when>
          <xsl:otherwise>&#x0302;</xsl:otherwise> <!-- default hat -->
        </xsl:choose>
      </mo>
    </mover>
  </xsl:template>

  <!-- m:bar  (overline / underline) -->
  <xsl:template match="m:bar">
    <xsl:choose>
      <xsl:when test="m:barPr/m:pos/@m:val = 'bot'">
        <munder xmlns="http://www.w3.org/1998/Math/MathML">
          <mrow><xsl:apply-templates select="m:e"/></mrow>
          <mo>&#x0332;</mo>
        </munder>
      </xsl:when>
      <xsl:otherwise>
        <mover xmlns="http://www.w3.org/1998/Math/MathML">
          <mrow><xsl:apply-templates select="m:e"/></mrow>
          <mo>&#x00AF;</mo>
        </mover>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- m:eqArr  (equation array) -->
  <xsl:template match="m:eqArr">
    <mtable xmlns="http://www.w3.org/1998/Math/MathML">
      <xsl:for-each select="m:e">
        <mtr><mtd><mrow><xsl:apply-templates/></mrow></mtd></mtr>
      </xsl:for-each>
    </mtable>
  </xsl:template>

  <!-- m:m  (matrix) -->
  <xsl:template match="m:m">
    <mfenced xmlns="http://www.w3.org/1998/Math/MathML" open="[" close="]">
      <mtable>
        <xsl:for-each select="m:mr">
          <mtr>
            <xsl:for-each select="m:e">
              <mtd><mrow><xsl:apply-templates/></mrow></mtd>
            </xsl:for-each>
          </mtr>
        </xsl:for-each>
      </mtable>
    </mfenced>
  </xsl:template>

  <!-- m:box -->
  <xsl:template match="m:box">
    <mrow xmlns="http://www.w3.org/1998/Math/MathML">
      <xsl:apply-templates select="m:e"/>
    </mrow>
  </xsl:template>

  <!-- m:borderBox -->
  <xsl:template match="m:borderBox">
    <menclose xmlns="http://www.w3.org/1998/Math/MathML" notation="box">
      <mrow><xsl:apply-templates select="m:e"/></mrow>
    </menclose>
  </xsl:template>

  <!-- Containers: m:e, m:sub, m:sup, m:deg, m:lim, m:fName -->
  <xsl:template match="m:e|m:sub|m:sup|m:deg|m:lim|m:fName">
    <xsl:apply-templates/>
  </xsl:template>

  <!-- Skip property elements -->
  <xsl:template match="m:rPr|m:ctrlPr|m:fPr|m:radPr|m:sSubPr|m:sSupPr|m:sSubSupPr|m:naryPr|m:dPr|m:funcPr|m:limLowPr|m:limUppPr|m:accPr|m:barPr|m:eqArrPr|m:mPr|m:boxPr|m:borderBoxPr|m:mcs"/>

  <!-- Catch-all: pass through children -->
  <xsl:template match="*">
    <xsl:apply-templates/>
  </xsl:template>

  <!-- Ignore text nodes that are not inside m:t -->
  <xsl:template match="text()"/>

</xsl:stylesheet>
