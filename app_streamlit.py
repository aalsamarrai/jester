import io
import zipfile
from pathlib import Path
import pandas as pd
import streamlit as st
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Jester", page_icon="📄", layout="centered")
st.title("📄 Jester Invoices")
st.write("Upload one or more Chile SII EnvioDTE XML files and get CSV line items.")

NS = {
    "sii": "http://www.sii.cl/SiiDte",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

def _txt(parent, xpath, default=None):
    if parent is None:
        return default
    el = parent.find(xpath, NS)
    if el is None or el.text is None:
        return default
    return el.text.strip()

def _int(parent, xpath):
    t = _txt(parent, xpath, None)
    if t in (None, ""):
        return None
    try:
        return int(t)
    except ValueError:
        try:
            return int(float(t))
        except Exception:
            return t

def parse_envio_dte_bytes(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    documentos = []
    for doc in root.findall(".//sii:DTE/sii:Documento", NS):
        enc = doc.find("sii:Encabezado", NS)
        iddoc = enc.find("sii:IdDoc", NS) if enc is not None else None

        documento = {
            "IdDoc": {
                "TipoDTE": _int(iddoc, "sii:TipoDTE"),
                "Folio": _int(iddoc, "sii:Folio"),
            },
            "Detalle": [],
        }
        for det in doc.findall("sii:Detalle", NS):
            item = {
                "NroLinDet": _int(det, "sii:NroLinDet"),
                "TpoCodigo": _txt(det.find("sii:CdgItem", NS), "sii:TpoCodigo"),
                "VlrCodigo": _txt(det.find("sii:CdgItem", NS), "sii:VlrCodigo"),
                "NmbItem": _txt(det, "sii:NmbItem"),
                "DscItem": _txt(det, "sii:DscItem"),
                "QtyItem": _int(det, "sii:QtyItem"),
                "PrcItem": _int(det, "sii:PrcItem"),
                "MontoItem": _int(det, "sii:MontoItem"),
            }
            documento["Detalle"].append(item)
        documentos.append(documento)
    return documentos

def items_dataframe(documentos):
    rows = []
    for d in documentos:
        folio = d.get("IdDoc", {}).get("Folio")
        tipodte = d.get("IdDoc", {}).get("TipoDTE")
        for it in d.get("Detalle", []):
            row = {"Folio": folio, "TipoDTE": tipodte}
            row.update(it)
            rows.append(row)
    df = pd.DataFrame(rows, columns=["Folio","TipoDTE","NroLinDet","TpoCodigo","VlrCodigo","NmbItem","DscItem","QtyItem","PrcItem","MontoItem"])
    return df

uploaded = st.file_uploader("Drop XML files here", type=["xml"], accept_multiple_files=True)

if uploaded:
    all_rows = []
    per_file_csv = {}
    for f in uploaded:
        try:
            docs = parse_envio_dte_bytes(f.read())
            df = items_dataframe(docs)
            all_rows.append(df)
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            per_file_csv[Path(f.name).with_suffix(".csv").name] = csv_bytes
            st.success(f"Parsed {f.name} ({len(df)} line items)")
            st.dataframe(df.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"Failed to parse {f.name}: {e}")

    if all_rows:
        merged = pd.concat(all_rows, ignore_index=True) if len(all_rows) > 1 else all_rows[0]
        st.subheader("Download")
        # Single merged CSV
        st.download_button(
            "⬇️ Download merged CSV",
            data=merged.to_csv(index=False).encode("utf-8"),
            file_name="dte_items_merged.csv",
            mime="text/csv",
        )
        # Zip with one CSV per input file
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in per_file_csv.items():
                zf.writestr(name, data)
        st.download_button(
            "⬇️ Download zip (one CSV per file)",
            data=buf.getvalue(),
            file_name="dte_items.zip",
            mime="application/zip",
        )
else:
    st.info("Tip: you can select multiple XMLs at once.")
