# Xendit Payment Integration Setup Guide

This guide will help you set up Xendit as the payment gateway for your DENR Portal application.

## 1. Prerequisites

- A Xendit account (sign up at https://xendit.co)
- Python 3.7+
- Your DENR Portal application running

## 2. Get Your Xendit Credentials

1. **Sign up or log in** to Xendit Dashboard: https://dashboard.xendit.co
2. **Navigate to Settings → Developers**
3. **Copy your credentials:**
   - **API Key** (Secret) - Keep this private, only use on backend
   - **Public Key** - Can be used on frontend

## 3. Install Xendit Package

The package is already added to `requirements.txt`. Install or update:

```bash
pip install xendit==2.9.0 requests==2.31.0
```

## 4. Configure Environment Variables

1. Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

2. **Edit `.env` and add your Xendit credentials:**

```env
XENDIT_API_KEY=your_actual_api_key_here
XENDIT_PUBLIC_KEY=your_actual_public_key_here
```

Get these from: https://dashboard.xendit.co/settings/developers

## 5. How Xendit Integration Works

### Payment Flow

1. **User selects a fisheries license/permit** in the payment form
2. **System creates a Xendit invoice** via `/api/payments/create-invoice`
3. **User is redirected** to Xendit checkout page
4. **User completes payment** using:
   - Credit/Debit Cards (Visa, Mastercard, JCB)
   - Bank Transfers (Virtual Accounts)
   - Over-the-Counter (7-Eleven, Robinsons, etc.)
5. **Xendit redirects** to success/failure page
6. **Webhook notification** updates payment status (optional)

### Payment Methods Available

| Method | Processing Time | Fees |
|--------|-----------------|------|
| Credit/Debit Card | Instant | 2.9% + ₱10 |
| Bank Transfer (VA) | 1-2 hours | ₱5,000 per VA |
| Retail (7-Eleven, etc) | 1-2 hours | ₱2,500 per transaction |
| E-wallet | Instant | Variable |

## 6. File Structure

After integration, you have:

### New Routes
- `GET /api/payments/payment-form/<service_type>` - Display payment form
- `POST /api/payments/create-invoice` - Create Xendit invoice
- `GET /api/payments/check-invoice/<invoice_id>` - Check payment status
- `POST /api/payments/webhook` - Handle Xendit webhooks
- `GET /payment-success` - Success redirect page
- `GET /payment-failed` - Failure redirect page

### New Templates
- `templates/payment-form.html` - Common payment form
- `templates/payment-success.html` - Success confirmation
- `templates/payment-failed.html` - Failure handling

### New Routes Module
- `routes/payments_routes.py` - Payment handling logic

## 7. Supported License Types & Pricing

The system supports these fisheries licenses with the following prices:

```python
servicePricing = {
    'aquafarm': ₱5,000 - Aquaculture Farm Registration
    'fish_transport': ₱2,500 - Fish Transport Permit
    'fish_dealer': ₱3,000 - Fish Dealer/Trade License
    'processing': ₱4,500 - Fish Processing Facility Permit
    'collection_harvest': ₱2,000 - Collection/Harvest Permit
}
```

To modify prices, edit `templates/payment-form.html` (line ~280) and `routes/payments_routes.py`.

## 8. Testing Payments

### Test Cards (Use in Sandbox Mode)

**Enable Sandbox Mode in Dashboard → Settings → Developers**

**Test Card Numbers:**
- Visa: `4111111111111111`
- Mastercard: `5200828282828210`
- JCB: `3530111333300000`

**Use any future expiry date and any 3-digit CVV**

## 9. Webhook Setup (Optional but Recommended)

To automatically update payment status when customers pay:

1. **Go to Dashboard → Settings → Developers → Webhooks**
2. **Add webhook endpoint:**
   ```
   https://your-domain.com/api/payments/webhook
   ```
3. **Select events:**
   - Invoice Paid
   - Invoice Expired

4. **Update `routes/payments_routes.py`** webhook function to process payments in your database

## 10. Customizing Payment Form

### Change Service Pricing

Edit `templates/payment-form.html` around line 265:

```javascript
const servicePricing = {
    'aquafarm': { name: 'Your Name', price: 5000 },
    // Add or modify services
};
```

### Change Payment Methods

In `routes/payments_routes.py`, modify the `payment_methods` list:

```python
'payment_methods': ['CREDIT_CARD', 'BANK_TRANSFER', 'RETAIL', 'EWALLET'],
```

### Customize Success/Failure Pages

Edit these templates:
- `templates/payment-success.html`
- `templates/payment-failed.html`

## 11. Troubleshooting

### "API Key not found" Error
- Check that `XENDIT_API_KEY` is set in `.env`
- Ensure you're using the **Secret Key**, not Public Key
- Verify the key is copied correctly with no extra spaces

### Payment Form not Loading
- Check browser console for JavaScript errors
- Ensure `XENDIT_PUBLIC_KEY` is set in config
- Verify payment form template is in correct location

### Webhook Not Receiving Notifications
- Confirm webhook URL is publicly accessible
- Check webhook logs in Xendit Dashboard
- Ensure your endpoint is not requiring authentication

### Transactions Not Appearing in Dashboard
- Check that invoice was created (check response)
- Verify merchant account is verified on Xendit
- Wait a few moments for dashboard to refresh

## 12. Production Checklist

Before going live:

- [ ] Update `XENDIT_API_KEY` and `XENDIT_PUBLIC_KEY` with production values
- [ ] Disable `DEBUG=True` in Flask config
- [ ] Set up proper email notifications
- [ ] Configure webhook for automatic payment processing
- [ ] Test full payment flow with real cards (use test mode first)
- [ ] Update terms and conditions in payment form
- [ ] Configure proper error logging
- [ ] Set up monitoring for failed transactions
- [ ] Document refund policy

## 13. API Reference

### Create Invoice
```bash
POST /api/payments/create-invoice
Content-Type: application/json

{
    "external_id": "invoice-12345",
    "first_name": "Juan",
    "last_name": "Dela Cruz",
    "email": "juan@example.com",
    "phone": "+639123456789",
    "amount": 5000,
    "item_name": "Aquaculture Farm Registration",
    "description": "License application #123",
    "success_url": "https://domain.com/payment-success",
    "failure_url": "https://domain.com/payment-failed"
}
```

### Check Invoice Status
```bash
GET /api/payments/check-invoice/<invoice_id>
```

Response:
```json
{
    "status": "success",
    "invoice_id": "xyz123",
    "amount": 5000,
    "paid_amount": 5000,
    "payment_status": "PAID",
    "paid_at": "2026-02-09T12:34:56Z",
    "payment_method": "CARD"
}
```

## 14. Support & Resources

- **Xendit Documentation:** https://xendit.readme.io
- **Dashboard:** https://dashboard.xendit.co
- **Support Email:** support@xendit.co
- **DENR Support:** support@denr.gov.ph

## 15. Security Notes

- Never expose `XENDIT_API_KEY` in frontend code
- Always use HTTPS in production
- Validate all webhook signatures
- Store payment records securely
- Implement proper logging for audit trails
- Regular security audits recommended

---

**Last Updated:** February 9, 2026
**Integration Version:** 1.0

Defenestration (The act of throwing someone out of a window)

Recursive (When a function calls itself, or things keep looping back)

Ziggurat (An ancient stepped pyramid structure)
