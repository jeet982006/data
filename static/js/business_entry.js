(function () {
    "use strict";

    const entryForm = document.getElementById("entryForm");
    const entryDateInput = document.getElementById("entry_date_picker");
    const entryDateHidden = document.getElementById("entry_date");
    const billAmount = document.getElementById("bill_amount");
    const entryId = document.getElementById("entry_id");
    const entryFormTitle = document.getElementById("entryFormTitle");
    const entrySubmitButton = document.getElementById("entrySubmitButton");
    const cancelEditButton = document.getElementById("cancelEditButton");

    const receivedForm = document.getElementById("receivedForm");
    const receivedDateInput = document.getElementById("received_date_picker");
    const receivedDateHidden = document.getElementById("received_date");
    
    const receivedId = document.getElementById("received_id");
    const amountReceivedInput = document.getElementById("amount_received");
    const receivedNoteInput = document.getElementById("received_note");
    const receivedSubmitButton = receivedForm ? receivedForm.querySelector(".received-enter-button") : null;

    if (entryForm && !entryForm.dataset.addAction) {
        entryForm.dataset.addAction = entryForm.action;
    }

    if (receivedForm && !receivedForm.dataset.addAction) {
        receivedForm.dataset.addAction = receivedForm.action;
    }

    const updatePopupOverlay = document.getElementById("updatePopupOverlay");
    const updatePopupClose = document.getElementById("updatePopupClose");
    const updatePopupCancel = document.getElementById("updatePopupCancel");
    const updatePopupConfirm = document.getElementById("updatePopupConfirm");
    const updatePopupMessage = document.getElementById("updatePopupMessage");

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    function todayDmy() {
        const d = new Date();
        return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();
    }

    function isValidDmy(value) {
        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value)) return false;
        const p = value.split("/");
        const day = Number(p[0]);
        const month = Number(p[1]);
        const year = Number(p[2]);
        const d = new Date(year, month - 1, day);
        return d.getFullYear() === year && d.getMonth() === month - 1 && d.getDate() === day;
    }

    function syncDates() {
        if (entryDateHidden && entryDateInput) {
            entryDateHidden.value = entryDateInput.value.trim();
        }
        if (receivedDateHidden && receivedDateInput) {
            receivedDateHidden.value = receivedDateInput.value.trim();
        }
    }

    function setToday() {
        const today = todayDmy();
        if (entryDateInput) entryDateInput.value = today;
        if (receivedDateInput) receivedDateInput.value = today;
        syncDates();
    }

    function closeUpdatePopup() {
        if (updatePopupOverlay) updatePopupOverlay.classList.remove("show");
    }

    function resetEntryForm() {
        if (!entryForm) return;
        entryForm.action = entryForm.dataset.addAction;
        if (entryId) entryId.value = "";
        if (billAmount) billAmount.value = "";
        if (entryFormTitle) entryFormTitle.textContent = "New Entry";
        if (entrySubmitButton) entrySubmitButton.textContent = "Enter";
        if (cancelEditButton) cancelEditButton.classList.add("hidden");
        setToday();
        closeUpdatePopup();
    }

    document.querySelectorAll(".js-edit-entry").forEach(function (button) {
        button.addEventListener("click", function () {
            const id = this.dataset.entryId || "";
            const date = this.dataset.entryDate || "";
            const bill = this.dataset.billAmount || "";

            if (entryId) entryId.value = id;
            if (entryDateInput) entryDateInput.value = date;
            if (entryDateHidden) entryDateHidden.value = date;
            if (billAmount) billAmount.value = bill;

            const businessId = entryForm ? entryForm.dataset.businessId : "";
            if (entryForm) {
                entryForm.action = "/business/" + encodeURIComponent(businessId) + "/update-entry/" + encodeURIComponent(id);
            }
            if (entryFormTitle) entryFormTitle.textContent = "Update Entry";
            if (entrySubmitButton) entrySubmitButton.textContent = "Update";
            if (cancelEditButton) cancelEditButton.classList.remove("hidden");
            
            if (entryForm) {
                entryForm.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

    document.querySelectorAll(".js-edit-received").forEach(function (button) {
        button.addEventListener("click", function () {
            const id = this.dataset.receivedId || "";
            const date = this.dataset.receivedDate || "";
            const amount = this.dataset.amountReceived || "";
            const note = this.dataset.note || "";

            if (receivedId) receivedId.value = id;
            if (receivedDateInput) receivedDateInput.value = date;
            if (receivedDateHidden) receivedDateHidden.value = date;
            if (amountReceivedInput) amountReceivedInput.value = amount;
            if (receivedNoteInput) receivedNoteInput.value = note;

            const businessId = entryForm ? entryForm.dataset.businessId : "";
            if (receivedForm) {
                receivedForm.action = "/business/" + encodeURIComponent(businessId) + "/update-received/" + encodeURIComponent(id);
            }
            if (receivedSubmitButton) {
                receivedSubmitButton.textContent = "Update";
            }
            if (receivedForm) {
                receivedForm.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

    if (cancelEditButton) cancelEditButton.addEventListener("click", resetEntryForm);
    if (updatePopupClose) updatePopupClose.addEventListener("click", closeUpdatePopup);
    if (updatePopupCancel) updatePopupCancel.addEventListener("click", closeUpdatePopup);
    if (updatePopupConfirm) updatePopupConfirm.addEventListener("click", closeUpdatePopup);
    if (updatePopupOverlay) {
        updatePopupOverlay.addEventListener("click", function (event) {
            if (event.target === updatePopupOverlay) closeUpdatePopup();
        });
    }

    function restrictDateTyping(input) {
        if (!input) return;
        input.addEventListener("input", function () {
            let value = this.value.replace(/[^0-9]/g, "");
            if (value.length > 2) value = value.slice(0, 2) + "/" + value.slice(2);
            if (value.length > 5) value = value.slice(0, 5) + "/" + value.slice(5, 9);
            this.value = value.slice(0, 10);
        });
    }

    restrictDateTyping(entryDateInput);
    restrictDateTyping(receivedDateInput);

    if (entryForm) {
        entryForm.addEventListener("submit", function (event) {
            syncDates();
            const date = entryDateInput ? entryDateInput.value.trim() : "";
            const bill = parseFloat(billAmount ? billAmount.value : "");

            if (!isValidDmy(date)) {
                event.preventDefault();
                alert("Please enter date in dd/mm/yyyy format. Example: 31/08/2026");
                if (entryDateInput) entryDateInput.focus();
                return;
            }
            if (Number.isNaN(bill) || bill < 0) {
                event.preventDefault();
                alert("Please enter a valid Bill Amount.");
                if (billAmount) billAmount.focus();
            }
        });
    }

    if (receivedForm) {
        receivedForm.addEventListener("submit", function (event) {
            syncDates();
            const date = receivedDateInput ? receivedDateInput.value.trim() : "";
            const amountInput = document.getElementById("amount_received");
            const amount = parseFloat(amountInput ? amountInput.value : "");

            if (!isValidDmy(date)) {
                event.preventDefault();
                alert("Please enter received date in dd/mm/yyyy format. Example: 31/08/2026");
                if (receivedDateInput) receivedDateInput.focus();
                return;
            }
            if (Number.isNaN(amount) || amount < 0) {
                event.preventDefault();
                alert("Please enter a valid Amount Received.");
                if (amountInput) amountInput.focus();
            }
        });
    }

    document.querySelectorAll(".delete-entry-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const row = this.closest("tr");
            const dateCell = row ? row.querySelector('[data-label="Date"]') : null;
            const date = dateCell ? dateCell.textContent.trim() : "";
            if (!window.confirm("Delete bill entry" + (date ? " of " + date : "") + "?\n\nThis cannot be undone.")) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll(".delete-received-form").forEach(function (form) {
        form.addEventListener("submit", function (event)  {
            const row = this.closest("tr");
            const dateCell = row ? row.querySelector('[data-label="Date"]') : null;
            const amountCell = row ? row.querySelector('[data-label="Amount Received"]') : null;
            const date = dateCell ? dateCell.textContent.trim() : "";
            const amount = amountCell ? amountCell.textContent.trim() : "";
            if (!window.confirm("Delete received amount?\n\nDate: " + date + "\nAmount: " + amount)) {
                event.preventDefault();
            }
        });
    });

    setToday();
})();
