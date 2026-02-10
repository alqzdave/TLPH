import { auth, onAuthStateChanged } from "./firebase-config.js";

const EMAIL_TIMEOUT_MS = 1500;
let cachedEmail = "";
let emailPromise = null;

function getCurrentUserEmail() {
    if (cachedEmail) {
        return Promise.resolve(cachedEmail);
    }
    if (emailPromise) {
        return emailPromise;
    }
    emailPromise = new Promise((resolve) => {
        const timeoutId = setTimeout(() => {
            resolve("");
        }, EMAIL_TIMEOUT_MS);

        const unsubscribe = onAuthStateChanged(auth, (user) => {
            clearTimeout(timeoutId);
            if (typeof unsubscribe === "function") {
                unsubscribe();
            }
            cachedEmail = user && user.email ? user.email : "";
            resolve(cachedEmail);
        });
    });

    return emailPromise;
}

function slugify(value) {
    return (value || "")
        .toString()
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
}

function getItemName(form) {
    return form.dataset.itemName
        || (document.querySelector("h1") && document.querySelector("h1").textContent.trim())
        || document.title
        || "License Application";
}

function getDescription(form, itemName) {
    return form.dataset.description || itemName;
}

function getExternalPrefix(form, itemName) {
    return form.dataset.externalPrefix || slugify(itemName) || "license";
}

function getSuccessUrl() {
    return window.location.href.split("#")[0];
}

function getFailureUrl() {
    return window.location.href.split("#")[0];
}

async function handlePaymentSubmit(event, form) {
    const amountInput = form.querySelector("#xendit_raw_amount");
    if (!amountInput) {
        return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();

    const submitBtn = form.querySelector("button[type='submit']");
    if (submitBtn) {
        submitBtn.disabled = true;
    }

    const amount = parseInt(amountInput.value, 10);
    const itemName = getItemName(form);
    const description = getDescription(form, itemName);
    const externalPrefix = getExternalPrefix(form, itemName);

    try {
        const email = await getCurrentUserEmail();
        const payload = {
            external_id: `${externalPrefix}-${Date.now()}`,
            amount: amount,
            email: email,
            description: description,
            item_name: itemName,
            success_url: getSuccessUrl(),
            failure_url: getFailureUrl()
        };

        const response = await fetch("/api/payments/create-invoice", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.status === "success" && result.invoice_url) {
            window.location.href = result.invoice_url;
            return;
        }

        const details = result.details ? `\n${JSON.stringify(result.details)}` : "";
        alert(`Payment error: ${result.message || "Unknown error"}${details}`);
    } catch (error) {
        console.error("Payment error:", error);
        alert("Failed to process payment. Please try again.");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }
}

function bindPayments() {
    const forms = Array.from(document.querySelectorAll("form"));
    forms.forEach((form) => {
        if (!form.querySelector("#xendit_raw_amount")) {
            return;
        }
        form.addEventListener(
            "submit",
            (event) => {
                handlePaymentSubmit(event, form);
            },
            true
        );
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindPayments);
} else {
    bindPayments();
}
