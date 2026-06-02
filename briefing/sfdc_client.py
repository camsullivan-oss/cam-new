"""Salesforce: pull account, opportunity, and contact data."""
import os
from simple_salesforce import Salesforce


def get_sf_client() -> Salesforce:
    sandbox = os.getenv("SFDC_SANDBOX", "false").lower() == "true"
    return Salesforce(
        username=os.getenv("SFDC_USERNAME"),
        password=os.getenv("SFDC_PASSWORD"),
        security_token=os.getenv("SFDC_SECURITY_TOKEN"),
        domain="test" if sandbox else "login",
    )


def get_account_data(company_name: str, contact_emails: list[str]) -> dict:
    """
    Look up Salesforce account by company name or contact email.
    Returns merged account + opportunity + contact data.
    """
    sf = get_sf_client()
    account = None
    opportunity = None
    contacts = []

    # Try finding account by contact email first (more precise)
    for email in contact_emails:
        result = sf.query(
            f"SELECT Id, AccountId, Name, Email FROM Contact WHERE Email = '{email}' LIMIT 1"
        )
        if result["records"]:
            record = result["records"][0]
            account_id = record.get("AccountId")
            if account_id:
                account = sf.Account.get(account_id)
                break

    # Fallback: search by company name
    if not account:
        result = sf.query(
            f"SELECT Id, Name, Industry, NumberOfEmployees, AnnualRevenue, "
            f"Website, BillingCountry, Type, OwnerId, Owner.Email, Owner.Name "
            f"FROM Account WHERE Name LIKE '%{company_name}%' LIMIT 1"
        )
        if result["records"]:
            account = result["records"][0]

    if not account:
        return {"found": False}

    account_id = account["Id"]

    # Get open opportunities
    opp_result = sf.query(
        f"SELECT Id, Name, StageName, Amount, CloseDate, "
        f"Probability, Description, "
        f"(SELECT FieldName__c, Value__c FROM OpportunityFieldHistory) "
        f"FROM Opportunity WHERE AccountId = '{account_id}' "
        f"AND IsClosed = false ORDER BY LastModifiedDate DESC LIMIT 1"
    )
    if opp_result["records"]:
        opportunity = opp_result["records"][0]

    # Get MEDPICC fields if they exist as custom fields on Opportunity
    medpicc_fields = {}
    if opportunity:
        opp_id = opportunity["Id"]
        try:
            medpicc_result = sf.query(
                f"SELECT Metrics__c, Economic_Buyer__c, Decision_Criteria__c, "
                f"Decision_Process__c, Identify_Pain__c, Champion__c, "
                f"Competition__c "
                f"FROM Opportunity WHERE Id = '{opp_id}' LIMIT 1"
            )
            if medpicc_result["records"]:
                medpicc_fields = medpicc_result["records"][0]
        except Exception:
            # MEDPICC fields may not exist as named above — skip gracefully
            pass

    # Get contacts associated with the account
    contacts_result = sf.query(
        f"SELECT Id, Name, Email, Title, Phone FROM Contact "
        f"WHERE AccountId = '{account_id}' LIMIT 10"
    )
    contacts = contacts_result.get("records", [])

    # Get recent activities / tasks
    activities_result = sf.query(
        f"SELECT Subject, Description, ActivityDate, Status "
        f"FROM Task WHERE AccountId = '{account_id}' "
        f"ORDER BY ActivityDate DESC LIMIT 5"
    )
    activities = activities_result.get("records", [])

    return {
        "found": True,
        "account": account,
        "opportunity": opportunity,
        "medpicc_fields": medpicc_fields,
        "contacts": contacts,
        "activities": activities,
    }
