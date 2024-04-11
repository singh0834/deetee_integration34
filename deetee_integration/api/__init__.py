import frappe
import json
from bs4 import BeautifulSoup
from frappe.utils import today, cstr


@frappe.whitelist()
def create_payment_entry(**data):
    try:
        customer_id = frappe.db.get_value(
            "Customer", {"customer_id": data.get("party")}, "name"
        )
        if not customer_id:
            return gen_response(500, "Customer doest not exists")
        payment_doc = frappe.get_doc(
            dict(
                doctype="Payment Entry",
                posting_date=data.get("date") or today(),
                payment_type=data.get("payment_type"),
                mode_of_payment=data.get("mode_of_payment"),
                party_type="Customer",
                party=customer_id,
                paid_from=data.get("from_account"),
                paid_to=data.get("to_account"),
                paid_amount=data.get("paid_amount"),
                received_amount=data.get("paid_amount"),
                reference_no=data.get("reference_no") or "sumup",
                reference_date=data.get("reference_date")
                or data.get("date")
                or today(),
                deetee_order=data.get("order"),
                advance_payment=data.get("advance_payment"),
            )
        )
        if not payment_doc.get("paid_from"):
            payment_doc.update(
                {
                    "paid_from": frappe.db.get_value(
                        "DeeTee Settings", "DeeTee Settings", "account_paid_from"
                    )
                }
            )
        if not payment_doc.get("paid_to"):
            payment_doc.update(
                {
                    "paid_to": frappe.db.get_value(
                        "DeeTee Settings", "DeeTee Settings", "account_paid_to"
                    )
                }
            )
        payment_doc.flags.ignore_permissions = True
        payment_doc.insert()
        return gen_response(200, "Payment added successfully")
    except Exception as e:
        frappe.log_error(title="DeeTee Integration Log", message=frappe.get_traceback())
        gen_response(500, cstr(e))


def gen_response(status, message, data=[]):
    frappe.response["http_status_code"] = status
    if status == 500:
        frappe.response["message"] = BeautifulSoup(str(message)).get_text()
    else:
        frappe.response["message"] = message
    frappe.response["data"] = data


@frappe.whitelist()
def create_sales_invoice(
    customer_id,
    date,
    items,
    agent_id=None,
    commission=0,
    payment_terms_id=None,
    bank_account_id=None,
    additional_invoice_details={},
    invoice_commercialterm={}
):
    try:
        customer_id = frappe.db.get_value(
            "Customer", {"customer_id": customer_id}, "name"
        )
        if not customer_id:
            return gen_response(500, "Customer doest not exists")
        # invoice_doc = frappe.new_doc("Sales Invoice")
        if isinstance(items, str):
            items = json.loads(items)
        for item in items:
            item["additionaloperation"] = json.dumps(item.get("additionaloperation"))
        sales_partner = frappe.db.get_value(
            "Sales Partner", {"crm_agent_id": agent_id}, "name"
        )
        invoice_doc = frappe.get_doc(
            dict(
                doctype="Sales Invoice",
                posting_date=date,
                customer=customer_id,
                items=items,
                sales_partner=sales_partner,
                commission_rate=commission,
                payment_terms_template=payment_terms_id,
                bank_account_id=bank_account_id,
                invoice_commercialterm=invoice_commercialterm,
                set_posting_time=1
            )
        )
        if isinstance(additional_invoice_details,str):
            additional_invoice_details =json.loads(additional_invoice_details)
        invoice_doc.update(additional_invoice_details)
        invoice_doc.invoice_boxno = json.dumps(additional_invoice_details.get("invoice_boxno"))
        invoice_doc.insert(ignore_permissions=True)
        return gen_response(200, "Invoice Created Successfully")
    except Exception as e:
        frappe.log_error(title="DeeTee Integration Log", message=frappe.get_traceback())
        gen_response(500, cstr(e))