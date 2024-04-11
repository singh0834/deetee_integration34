import frappe
import requests
import json
from frappe.utils import cint, flt, cstr, now
from frappe.utils.background_jobs import enqueue

BASE_URL = "http://43.205.13.23"


@frappe.whitelist()
def get_deetee_data(document):
    if document == "Item":
        enqueue(_get_deetee_items, queue="long", timeout=6000)
    if document == "Customer":
        enqueue(_get_deetee_customers, queue="long", timeout=6000)
    if document == "Payment Terms Template":
        enqueue(_get_deetee_payment_terms, queue="long", timeout=6000)
    frappe.db.commit()

@frappe.whitelist()
def _get_deetee_data():
    enqueue(_get_deetee_items, queue="long", timeout=6000)
    enqueue(_get_deetee_customers, queue="long", timeout=6000)
    enqueue(_get_deetee_payment_terms, queue="long", timeout=6000)
    frappe.db.commit()

@frappe.whitelist()
def _get_deetee_items():
    try:
        api_url = f"{BASE_URL}/deetee/public/api/get/OH_item"
        data = {}
        headers = {"Authorization": "Basic RGVlVGVlOkRUQDEyMyMkJCM="}
        r = requests.request(
            method="GET",
            url=api_url,
            data=json.dumps(data, default=str),
            headers=headers,
        )
        print("call")
        r.raise_for_status()
        log_request(
            api_url, headers, data, r, integration_request_service="DeeTee Item fetch"
        )
        if r and r.text:
            create_document(r.text, "Item")
            update_sync("Item")
    except Exception as e:
        frappe.log_error(
            title="Error DeeTee Item Featch API", message=frappe.get_traceback()
        )
        frappe.db.rollback()



@frappe.whitelist()
def _get_deetee_payment_terms():
    try:
        api_url = f"{BASE_URL}/deetee/public/api/get/OH_paymentTerm"
        data = {}
        headers = {"Authorization": "Basic RGVlVGVlOkRUQDEyMyMkJCM="}
        r = requests.request(
            method="GET",
            url=api_url,
            data=json.dumps(data, default=str),
            headers=headers,
        )
        print("call")
        r.raise_for_status()
        log_request(
            api_url, headers, data, r, integration_request_service="DeeTee Payment Terms fetch"
        )
        if r and r.text:
            create_document(r.text, "Payment Terms Template")
            update_sync("Payment Terms Template")
    except Exception as e:
        frappe.log_error(
            title="Error DeeTee Payment Terms Featch API", message=frappe.get_traceback()
        )
        frappe.db.rollback()

# @frappe.whitelist()
# def get_deetee_customers():
#     enqueue(_get_deetee_customers, queue="long", timeout=6000)


@frappe.whitelist()
def _get_deetee_customers():
    try:
        api_url = f"{BASE_URL}/deetee/public/api/get/OH_customer"
        data = {}
        headers = {"Authorization": "Basic RGVlVGVlOkRUQDEyMyMkJCM="}
        r = requests.request(
            method="GET",
            url=api_url,
            data=json.dumps(data, default=str),
            headers=headers,
        )
        print("call")
        print(api_url)
        r.raise_for_status()
        log_request(
            api_url,
            headers,
            data,
            r,
            integration_request_service="DeeTee Customer fetch",
        )
        if r and r.text:
            create_document(r.text, "Customer")
            update_sync("Customer")
    except Exception as e:
        frappe.log_error(
            title="Error DeeTee Customer Featch API", message=frappe.get_traceback()
        )
        frappe.db.rollback()


def update_sync(doctype):
    settings_doc = frappe.get_doc("DeeTee Settings", "DeeTee Settings")
    exists = False
    for row in settings_doc.deetee_settings_details:
        if row.document == doctype:
            row.last_sync = now()
            exists = True
            break
    if not exists:
        settings_doc.append(
            "deetee_settings_details", dict(document=doctype, last_sync=now())
        )
    settings_doc.save()


def create_document(data, doctype):
    if isinstance(data, str):
        data = json.loads(data)
    if doctype == "Payment Terms Template":
        create_payment_terms_template(data)
        return
    mapping_details = frappe.get_doc("DeeTee Mapping", doctype)
    if mapping_details:
        for row_data in data:
            filters = {}
            for row_unique in mapping_details.deetee_mapping_unique:
                filters[row_unique.get("frappe_field")] = row_data.get(
                    row_unique.get("deetee_field")
                )
            if filters and frappe.db.exists(doctype, filters):
                document_id = frappe.db.get_value(doctype, filters, "name")
                doc = frappe.get_doc(doctype, document_id)
            else:
                if not row_data.get(mapping_details.get("unique_field")):
                    continue
                doc = frappe.new_doc(doctype)
            field_map = {}
            for row_map in mapping_details.deetee_mapping_details:
                # frappe.log_error(title="52", message=row_map.as_json())
                convert_value(row_data=row_data, row_map=row_map)
                # frappe.log_error(title="54", message=row_map)
                field_map[row_map.get("frappe_field")] = row_data.get(
                    row_map.get("deetee_field")
                ) or row_map.get("default_value")
            doc.update(field_map)
            if doc:
                doc.save(ignore_permissions=True)
                if doctype == "Customer":
                    create_address(data=row_data,customer_id=doc.name)
    else:
        frappe.throw(f"{doctype}: Mapping Details not created")


def create_payment_terms_template(data):
    for key,values in data.items():
        if frappe.db.exists("Payment Terms Template",key):
            payment_term_template_doc = frappe.get_doc("Payment Terms Template",key)
            payment_term_template_doc.terms = []
        else:
            payment_term_template_doc = frappe.new_doc("Payment Terms Template")
        payment_term_template_doc.template_name = key
        for row in values:
            payment_term_template_doc.append("terms",dict(
                description = row.get("paymentterm_condition"),
                invoice_portion = cint(row.get("peyment_term_percentage")),
                credit_days = row.get("days")
            ))
        payment_term_template_doc.flags.ignore_validate = True
        payment_term_template_doc.save(ignore_permissions = True)

# def create_payment_terms(data):
#     payment_term_doc = frappe.new_doc("Payment Terms")
#     payment_term_doc.payment_term_name = data.get("peyment_term_name")
#     payment_term_doc.invoice_portion = cint(data.get("peyment_term_percentage"))
#     payment_term_doc.credit_days = data.get("days")
#     payment_term_doc.description = data.get("paymentterm_condition")
#     payment_term_doc.insert(ignore_permissions = True)


def create_address(data,customer_id):
    if data.get("customer_billadrline1") and data.get("bill_city_name") and data.get("bill_country_name"):
        address_doc = frappe.new_doc("Address")
        address_doc.address_line1 = data.get("customer_billadrline1")
        billing_add_2 = ""
        if data.get("customer_billadrline2"):
            billing_add_2 = data.get("customer_billadrline2")
        if data.get("customer_billadrline3"):
            billing_add_2 += data.get("customer_billadrline3")
        address_doc.address_line2 = billing_add_2
        address_doc.is_primary_address = 1
        address_doc.city = data.get("bill_city_name")
        address_doc.state = data.get("bill_state_name")
        address_doc.country = data.get("bill_country_name")
        address_doc.pincode = data.get("customer_billpincode")
        address_doc.gstin = data.get("customer_gstno")
        address_doc.append("links",dict(
            link_doctype = "Customer",
            link_name = customer_id
        ))
        address_doc.flags.ignore_validate = True
        address_doc.flags.ignore_mandatory = True
        address_doc.insert(ignore_permissions = True)

    if data.get("customer_shipadrline1") and data.get("ship_city_name") and data.get("ship_country_name"):
        address_doc = frappe.new_doc("Address")
        address_doc.address_line1 = data.get("customer_shipadrline1")
        shipping_add_2 = ""
        if data.get("customer_shipadrline2"):
            shipping_add_2 = data.get("customer_shipadrline2")
        if data.get("customer_shipadrline3"):
            shipping_add_2 += data.get("customer_shipadrline3")
        address_doc.address_line2 = shipping_add_2
        address_doc.is_shipping_address = 1
        address_doc.city = data.get("ship_city_name")
        address_doc.state = data.get("ship_state_name")
        address_doc.country = data.get("ship_country_name")
        address_doc.pincode = data.get("customer_shippincode")
        address_doc.gstin = data.get("customer_gstno")
        address_doc.append("links",dict(
            link_doctype = "Customer",
            link_name = customer_id
        ))
        address_doc.flags.ignore_validate = True
        address_doc.flags.ignore_mandatory = True
        address_doc.insert(ignore_permissions = True)

def convert_value(row_data, row_map):
    if row_map.get("convert"):
        field_update = {}
        if row_map.get("convert") == "Int":
            field_update[row_map.get("deetee_field")] = cint(
                row_data.get(row_map.get("deetee_field"))
            )
            # row_map.deetee_field = cint(row_map.get("deetee_field"))
        if row_map.get("convert") == "Str":
            field_update[row_map.get("deetee_field")] = cstr(
                row_data.get(row_map.get("deetee_field"))
            )
            # row_map.deetee_field = cstr(row_map.get("deetee_field"))
        if row_map.get("convert") == "Float":
            field_update[row_map.get("deetee_field")] = flt(
                row_data.get(row_map.get("deetee_field"))
            )
        # frappe.log_error(title="84", message=field_update)
        row_data.update(field_update)
        # frappe.log_error(title="86", message=row_data)
        # row_map.deetee_field = flt(row_map.get("deetee_field"


def log_request(url, headers, data=None, res=None, integration_request_service=None):
    try:
        request_log = frappe.get_doc(
            {
                "doctype": "DeeTee Integration Log",
                "integration_request_service": integration_request_service,
                "request_description": integration_request_service,
                "status": "Completed",
                "url": url,
                "request_headers": frappe.as_json(headers) if headers else None,
                "data": frappe.as_json(data) if data else None,
                "output": res and res.text,
                "error": frappe.get_traceback(),
            }
        )
        request_log.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            title="DeeTee Integration API Log Error", message=frappe.get_traceback()
        )


@frappe.whitelist()
def get_deetee_item_wise_valuation():
    try:
        api_url = f"{BASE_URL}/deetee/public/api/get/fg_item_wise_valuation"
        data = {}
        headers = {}
        r = requests.request(
            method="GET",
            url=api_url,
            data=json.dumps(data, default=str),
            headers=headers,
        )
        print("call")
        r.raise_for_status()
        log_request(
            api_url,
            headers,
            data,
            r,
            integration_request_service="DeeTee Item Wise Valuation",
        )

        deetee_data = r.json()

        create_stock_reconciliation(deetee_data)

        return r.json()

    except Exception as e:
        frappe.log_error(
            title="Error DeeTee Item Wise Valuation Featch API",
            message=frappe.get_traceback(),
        )


def create_stock_reconciliation(deetee_data):
    stock_rec_doc = frappe.new_doc("Stock Reconciliation")
    stock_rec_doc.posting_date = (frappe.utils.nowdate(),)
    stock_rec_doc.purpose = "Stock Reconciliation"
    # stock_rec_doc.expense_account="Stock In Hand - DT"
    for item_data in deetee_data:
        warehouse, qty, valuation = get_warehouse(item_data)
        item_code = frappe.db.get_value(
            "Item", {"item_id": item_data.get("item_id")}, "name"
        )
        if item_code:
            stock_rec_doc.append(
                "items",
                dict(
                    item_code=item_code,
                    warehouse=warehouse,
                    qty=qty,
                    valuation_rate=valuation / qty,
                ),
            )

    try:
        stock_rec_doc.insert(ignore_permissions=True)
        stock_rec_doc.flags.ignore_permissions = True
        stock_rec_doc.submit()
        return "Stock Adjusted"
    except Exception as e:
        frappe.log_error(
            title="Error Creating Stock Reconciliation", message=frappe.get_traceback()
        )


def get_warehouse(item_data):
    fg_qty = cint(item_data.get("fg_qty"))
    if fg_qty > 0:
        return (
            frappe.db.get_value(
                "DeeTee Unit", item_data.get("unit_id"), "fg_warehouse"
            ),
            fg_qty,
            flt(item_data.get("fg_value")),
        )

    wip_qty = cint(item_data.get("wip_qty"))
    if wip_qty > 0:
        return (
            frappe.db.get_value(
                "DeeTee Unit", item_data.get("unit_id"), "wip_warehouse"
            ),
            wip_qty,
            flt(item_data.get("wip_value")),
        )
