def parse_envio_dte_bytes(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    documentos = []

    # Case 1: EnvioDTE (wrapped)
    docs = root.findall(".//sii:DTE/sii:Documento", NS)
    # Case 2: Bare DTE (root is <DTE>)
    if not docs:
        docs = root.findall(".//sii:Documento", NS)
        if not docs and root.tag.endswith("Documento"):
            docs = [root]

    for doc in docs:
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
