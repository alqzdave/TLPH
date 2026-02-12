import { submitServiceRequest, submitFreeServiceRequest } from '/static/js/service-request-handler.js';

function getServiceType(form) {
  if (form.dataset.serviceType) {
    return form.dataset.serviceType.trim();
  }

  const heading = document.querySelector('h1, h2');
  if (heading && heading.textContent) {
    return heading.textContent.trim();
  }

  return document.title.replace(/\s*-\s*DENR.*$/i, '').trim() || 'Service Request';
}

function getSubmitButton(form, index) {
  let btn = form.querySelector('button[type="submit"], input[type="submit"]');
  if (!btn) return null;

  if (!btn.id) {
    btn.id = `service-submit-${index}`;
  }

  return btn;
}

function attachAutoHandler(form, index) {
  if (form.dataset.serviceHandler) return;

  const submitBtn = getSubmitButton(form, index);
  if (!submitBtn) return;

  if (!form.id) {
    form.id = `service-form-${index}`;
  }

  const serviceType = getServiceType(form);
  const feeInput = form.querySelector('#xendit_raw_amount');
  const amount = feeInput ? parseInt(feeInput.value, 10) || 0 : 0;
  const itemName = `${serviceType} Service`;
  const description = `${serviceType} Service Fee`;
  const successUrl = `${window.location.origin}/user/service-confirmation`;
  const failureUrl = window.location.href;

  const config = {
    formId: form.id,
    submitBtnId: submitBtn.id,
    serviceType,
    amount,
    itemName,
    description,
    successUrl,
    failureUrl
  };

  if (amount > 0) {
    submitServiceRequest(config);
  } else {
    submitFreeServiceRequest(config);
  }

  form.dataset.serviceHandler = 'auto';
}

function isServicePage() {
  const path = window.location.pathname.toLowerCase();
  return (
    path.includes('/user/service/') ||
    path.includes('/user/compensation/') ||
    path.includes('/user/seminar/')
  );
}

document.addEventListener('DOMContentLoaded', () => {
  if (!isServicePage()) return;

  const forms = Array.from(document.querySelectorAll('form'));
  forms.forEach((form, index) => attachAutoHandler(form, index + 1));
});
