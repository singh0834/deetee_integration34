import frappe
import json


def drop_custom_field():

    deleted_documents = frappe.get_all("Deleted Document",filters={},fields=["name"])
    for row in deleted_documents:
        deleted_document_doc = frappe.get_doc("Deleted Document",row.get("name"))
        data = deleted_document_doc.get("data")
        if isinstance(data,str):
            data = json.loads(data)
        if data.get("dt") == "Sales Invoice":
            try:
                frappe.db.sql("""ALTER TABLE `tabSales Invoice` DROP COLUMN {0}""".format(data.get("fieldname")))
                print(f"{data.get('fieldname')} deleted")
            except Exception as e:
                print(e)
