from pathlib import Path
import json
from lxml import etree

KPI_FILE = Path("raga/kpis.json")
OUT_XML  = Path("xbrl/informe.xbrl")
XSD_FILE = Path("xbrl/schema/basic_xbrl.xsd")
VAL_LOG  = Path("xbrl/validation.log")

def build_xml(entity="ACME", period="2024-01"):
    ns = {"x": "http://example.com/xbrl"}
    root = etree.Element("{http://example.com/xbrl}Report", version="0.1")
    etree.SubElement(root, "{http://example.com/xbrl}Entity").text = entity
    etree.SubElement(root, "{http://example.com/xbrl}Period").text = period
    kpis = json.loads(KPI_FILE.read_text(encoding="utf-8"))
    for k, v in kpis.items():
        kpi = etree.SubElement(root, "{http://example.com/xbrl}KPI")
        etree.SubElement(kpi, "{http://example.com/xbrl}Id").text = k
        etree.SubElement(kpi, "{http://example.com/xbrl}Value").text = str(v)
        # opcional: unidad por KPI si quieres
        # etree.SubElement(kpi, "{http://example.com/xbrl}Unit").text = "tCO2e"  # etc.
    return root

def validate_xml(xml_tree):
    schema_doc = etree.parse(str(XSD_FILE))
    schema = etree.XMLSchema(schema_doc)
    return schema.validate(xml_tree), schema.error_log

def main():
    OUT_XML.parent.mkdir(parents=True, exist_ok=True)
    xml = build_xml()
    tree = etree.ElementTree(xml)
    ok, errors = validate_xml(tree)
    tree.write(str(OUT_XML), encoding="utf-8", xml_declaration=True, pretty_print=True)

    if ok:
        VAL_LOG.write_text("XBRL basic schema validation: OK\n", encoding="utf-8")
        print("XBRL OK →", OUT_XML)
    else:
        VAL_LOG.write_text("XBRL validation: FAILED\n" + str(errors), encoding="utf-8")
        print("XBRL FAILED. See", VAL_LOG)

if __name__ == "__main__":
    main()
