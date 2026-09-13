(function () {
    "use strict";


    /* =====================================================
       ELEMENTS
    ====================================================== */

    const entryForm = document.getElementById("entryForm");
    const entryDateInput = document.getElementById("entry_date_picker");
    const entryDateHidden = document.getElementById("entry_date");
    const entryHiddenDatePicker = document.getElementById("entryHiddenDatePicker");
    const entryCalendarButton = document.getElementById("entryCalendarButton");

    const billAmount = document.getElementById("bill_amount");

    const entryId = document.getElementById("entry_id");
    const entryFormTitle = document.getElementById("entryFormTitle");
    const entrySubmitButton = document.getElementById("entrySubmitButton");
    const cancelEditButton = document.getElementById("cancelEditButton");


    const receivedForm = document.getElementById("receivedForm");

    const receivedDateInput = document.getElementById("received_date_picker");
    const receivedDateHidden = document.getElementById("received_date");
    const receivedHiddenDatePicker = document.getElementById(
        "receivedHiddenDatePicker"
    );
    const receivedCalendarButton = document.getElementById(
        "receivedCalendarButton"
    );

    const receivedId = document.getElementById("received_id");
    const amountReceivedInput = document.getElementById("amount_received");
    const receivedNoteInput = document.getElementById("received_note");

    const receivedSubmitButton = receivedForm
        ? receivedForm.querySelector(".received-enter-button")
        : null;


    /* =====================================================
       FORM ACTION
    ====================================================== */

    if (entryForm && !entryForm.dataset.addAction) {
        entryForm.dataset.addAction = entryForm.action;
    }

    if (receivedForm && !receivedForm.dataset.addAction) {
        receivedForm.dataset.addAction = receivedForm.action;
    }


    /* =====================================================
       UPDATE POPUP
    ====================================================== */

    const updatePopupOverlay = document.getElementById(
        "updatePopupOverlay"
    );

    const updatePopupClose = document.getElementById(
        "updatePopupClose"
    );

    const updatePopupCancel = document.getElementById(
        "updatePopupCancel"
    );

    const updatePopupConfirm = document.getElementById(
        "updatePopupConfirm"
    );

    const updatePopupMessage = document.getElementById(
        "updatePopupMessage"
    );


    /* =====================================================
       DATE HELPERS
    ====================================================== */

    function pad(number) {
        return String(number).padStart(2, "0");
    }


    function todayDmy() {
        const date = new Date();

        return (
            pad(date.getDate()) +
            "/" +
            pad(date.getMonth() + 1) +
            "/" +
            date.getFullYear()
        );
    }


    function dmyToIso(value) {
        if (!value) {
            return "";
        }

        const parts = value.trim().split("/");

        if (parts.length !== 3) {
            return "";
        }

        const day = parts[0];
        const month = parts[1];
        const year = parts[2];

        if (
            day.length !== 2 ||
            month.length !== 2 ||
            year.length !== 4
        ) {
            return "";
        }

        return year + "-" + month + "-" + day;
    }


    function isoToDmy(value) {
        if (!value) {
            return "";
        }

        const parts = value.split("-");

        if (parts.length !== 3) {
            return "";
        }

        const year = parts[0];
        const month = parts[1];
        const day = parts[2];

        if (
            year.length !== 4 ||
            month.length !== 2 ||
            day.length !== 2
        ) {
            return "";
        }

        return day + "/" + month + "/" + year;
    }


    function isValidDmy(value) {

        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
            return false;
        }

        const parts = value.split("/");

        const day = Number(parts[0]);
        const month = Number(parts[1]);
        const year = Number(parts[2]);

        if (
            day < 1 ||
            month < 1 ||
            month > 12 ||
            year < 1900
        ) {
            return false;
        }

        const date = new Date(
            year,
            month - 1,
            day
        );

        return (
            date.getFullYear() === year &&
            date.getMonth() === month - 1 &&
            date.getDate() === day
        );
    }


    /* =====================================================
       FORMAT MANUAL DATE TYPING
    ====================================================== */

    function formatDateInput(input) {

        if (!input) {
            return;
        }

        input.addEventListener("input", function () {

            let value = this.value.replace(/\D/g, "");

            if (value.length > 2) {
                value =
                    value.slice(0, 2) +
                    "/" +
                    value.slice(2);
            }

            if (value.length > 5) {
                value =
                    value.slice(0, 5) +
                    "/" +
                    value.slice(5, 9);
            }

            this.value = value.slice(0, 10);

        });
    }


    /* =====================================================
       CALENDAR SETUP
    ====================================================== */

    function setupCalendar(
        button,
        datePicker,
        textInput,
        hiddenInput
    ) {

        if (
            !button ||
            !datePicker ||
            !textInput ||
            !hiddenInput
        ) {
            return;
        }


        /* ---------------------------------------------
           CALENDAR BUTTON
        ---------------------------------------------- */

        button.addEventListener("click", function () {

            /*
             * First put current text date into
             * native date picker.
             */

            const isoDate = dmyToIso(
                textInput.value.trim()
            );

            if (isValidDmy(textInput.value.trim())) {
                datePicker.value = isoDate;
            } else if (!datePicker.value) {
                datePicker.value = dmyToIso(
                    todayDmy()
                );
            }


            /*
             * Open native calendar.
             */

            try {

                if (typeof datePicker.showPicker === "function") {
                    datePicker.showPicker();
                } else {
                    datePicker.focus();
                    datePicker.click();
                }

            } catch (error) {

                datePicker.focus();
                datePicker.click();

            }

        });


        /* ---------------------------------------------
           CALENDAR DATE SELECT
        ---------------------------------------------- */

        datePicker.addEventListener("change", function () {

            if (!this.value) {
                return;
            }

            const formattedDate = isoToDmy(
                this.value
            );

            textInput.value = formattedDate;
            hiddenInput.value = formattedDate;

        });


        /* ---------------------------------------------
           MANUAL INPUT
        ---------------------------------------------- */

        textInput.addEventListener("input", function () {

            const value = this.value.trim();

            if (isValidDmy(value)) {

                hiddenInput.value = value;

                const iso = dmyToIso(value);

                if (iso) {
                    datePicker.value = iso;
                }

            } else {

                hiddenInput.value = value;

            }

        });


        /* ---------------------------------------------
           BLUR
        ---------------------------------------------- */

        textInput.addEventListener("blur", function () {

            const value = this.value.trim();

            if (isValidDmy(value)) {

                hiddenInput.value = value;

                const iso = dmyToIso(value);

                if (iso) {
                    datePicker.value = iso;
                }

            }

        });

    }


    /* =====================================================
       SYNC DATES
    ====================================================== */

    function syncDates() {

        if (
            entryDateHidden &&
            entryDateInput
        ) {

            entryDateHidden.value =
                entryDateInput.value.trim();

        }


        if (
            receivedDateHidden &&
            receivedDateInput
        ) {

            receivedDateHidden.value =
                receivedDateInput.value.trim();

        }

    }


    /* =====================================================
       SET TODAY
    ====================================================== */

    function setToday() {

        const today = todayDmy();
        const todayIso = dmyToIso(today);


        if (entryDateInput) {
            entryDateInput.value = today;
        }

        if (entryDateHidden) {
            entryDateHidden.value = today;
        }

        if (entryHiddenDatePicker) {
            entryHiddenDatePicker.value = todayIso;
        }


        if (receivedDateInput) {
            receivedDateInput.value = today;
        }

        if (receivedDateHidden) {
            receivedDateHidden.value = today;
        }

        if (receivedHiddenDatePicker) {
            receivedHiddenDatePicker.value = todayIso;
        }

    }


    /* =====================================================
       CLOSE UPDATE POPUP
    ====================================================== */

    function closeUpdatePopup() {

        if (updatePopupOverlay) {
            updatePopupOverlay.classList.remove("show");
        }

    }


    /* =====================================================
       RESET ENTRY FORM
    ====================================================== */

    function resetEntryForm() {

        if (!entryForm) {
            return;
        }


        entryForm.action =
            entryForm.dataset.addAction;


        if (entryId) {
            entryId.value = "";
        }


        if (billAmount) {
            billAmount.value = "";
        }


        if (entryFormTitle) {
            entryFormTitle.textContent =
                "New Entry";
        }


        if (entrySubmitButton) {
            entrySubmitButton.textContent =
                "Enter";
        }


        if (cancelEditButton) {
            cancelEditButton.classList.add(
                "hidden"
            );
        }


        setToday();

        closeUpdatePopup();

    }


    /* =====================================================
       RESET RECEIVED FORM
    ====================================================== */

    function resetReceivedForm() {

        if (!receivedForm) {
            return;
        }


        receivedForm.action =
            receivedForm.dataset.addAction ||
            receivedForm.action;


        if (receivedId) {
            receivedId.value = "";
        }


        if (amountReceivedInput) {
            amountReceivedInput.value = "";
        }


        if (receivedNoteInput) {
            receivedNoteInput.value = "";
        }


        if (receivedSubmitButton) {
            receivedSubmitButton.textContent =
                "Enter";
        }


        if (receivedDateInput) {
            receivedDateInput.value =
                todayDmy();
        }


        if (receivedDateHidden) {
            receivedDateHidden.value =
                todayDmy();
        }


        if (receivedHiddenDatePicker) {
            receivedHiddenDatePicker.value =
                dmyToIso(todayDmy());
        }

    }


    /* =====================================================
       EDIT BILL ENTRY
    ====================================================== */

    document
        .querySelectorAll(".js-edit-entry")
        .forEach(function (button) {

            button.addEventListener(
                "click",
                function () {

                    const id =
                        this.dataset.entryId || "";

                    const date =
                        this.dataset.entryDate || "";

                    const bill =
                        this.dataset.billAmount || "";


                    if (entryId) {
                        entryId.value = id;
                    }


                    if (entryDateInput) {
                        entryDateInput.value = date;
                    }


                    if (entryDateHidden) {
                        entryDateHidden.value = date;
                    }


                    if (entryHiddenDatePicker) {

                        entryHiddenDatePicker.value =
                            dmyToIso(date);

                    }


                    if (billAmount) {
                        billAmount.value = bill;
                    }


                    const businessId =
                        entryForm
                            ? entryForm.dataset.businessId
                            : "";


                    if (entryForm) {

                        entryForm.action =
                            "/business/" +
                            encodeURIComponent(businessId) +
                            "/update-entry/" +
                            encodeURIComponent(id);

                    }


                    if (entryFormTitle) {
                        entryFormTitle.textContent =
                            "Update Entry";
                    }


                    if (entrySubmitButton) {
                        entrySubmitButton.textContent =
                            "Update";
                    }


                    if (cancelEditButton) {
                        cancelEditButton.classList.remove(
                            "hidden"
                        );
                    }


                    if (entryForm) {

                        entryForm.scrollIntoView({
                            behavior: "smooth",
                            block: "center"
                        });

                    }

                }
            );

        });


    /* =====================================================
       EDIT RECEIVED ENTRY
    ====================================================== */

    document
        .querySelectorAll(".js-edit-received")
        .forEach(function (button) {

            button.addEventListener(
                "click",
                function () {

                    const id =
                        this.dataset.receivedId || "";

                    const date =
                        this.dataset.receivedDate || "";

                    const amount =
                        this.dataset.amountReceived || "";

                    const note =
                        this.dataset.note || "";


                    if (receivedId) {
                        receivedId.value = id;
                    }


                    if (receivedDateInput) {
                        receivedDateInput.value = date;
                    }


                    if (receivedDateHidden) {
                        receivedDateHidden.value = date;
                    }


                    if (receivedHiddenDatePicker) {
                        receivedHiddenDatePicker.value =
                            dmyToIso(date);
                    }


                    if (amountReceivedInput) {
                        amountReceivedInput.value =
                            amount;
                    }


                    if (receivedNoteInput) {
                        receivedNoteInput.value =
                            note;
                    }


                    const businessId =
                        entryForm
                            ? entryForm.dataset.businessId
                            : "";


                    if (receivedForm) {

                        receivedForm.action =
                            "/business/" +
                            encodeURIComponent(businessId) +
                            "/update-received/" +
                            encodeURIComponent(id);

                    }


                    if (receivedSubmitButton) {
                        receivedSubmitButton.textContent =
                            "Update";
                    }


                    if (receivedForm) {

                        receivedForm.scrollIntoView({
                            behavior: "smooth",
                            block: "center"
                        });

                    }

                }
            );

        });


    /* =====================================================
       CANCEL BILL UPDATE
    ====================================================== */

    if (cancelEditButton) {

        cancelEditButton.addEventListener(
            "click",
            resetEntryForm
        );

    }


    /* =====================================================
       POPUP EVENTS
    ====================================================== */

    if (updatePopupClose) {

        updatePopupClose.addEventListener(
            "click",
            closeUpdatePopup
        );

    }


    if (updatePopupCancel) {

        updatePopupCancel.addEventListener(
            "click",
            closeUpdatePopup
        );

    }


    if (updatePopupConfirm) {

        updatePopupConfirm.addEventListener(
            "click",
            closeUpdatePopup
        );

    }


    if (updatePopupOverlay) {

        updatePopupOverlay.addEventListener(
            "click",
            function (event) {

                if (
                    event.target ===
                    updatePopupOverlay
                ) {

                    closeUpdatePopup();

                }

            }
        );

    }


    /* =====================================================
       DATE INPUT FORMATTING
    ====================================================== */

    formatDateInput(entryDateInput);
    formatDateInput(receivedDateInput);


    /* =====================================================
       CALENDAR INITIALIZATION
    ====================================================== */

    setupCalendar(
        entryCalendarButton,
        entryHiddenDatePicker,
        entryDateInput,
        entryDateHidden
    );


    setupCalendar(
        receivedCalendarButton,
        receivedHiddenDatePicker,
        receivedDateInput,
        receivedDateHidden
    );


    /* =====================================================
       BILL ENTRY SUBMIT
    ====================================================== */

    if (entryForm) {

        entryForm.addEventListener(
            "submit",
            function (event) {

                syncDates();


                const date =
                    entryDateInput
                        ? entryDateInput.value.trim()
                        : "";


                const bill =
                    parseFloat(
                        billAmount
                            ? billAmount.value
                            : ""
                    );


                if (!isValidDmy(date)) {

                    event.preventDefault();

                    alert(
                        "Please enter date in dd/mm/yyyy format. Example: 31/08/2026"
                    );

                    if (entryDateInput) {
                        entryDateInput.focus();
                    }

                    return;

                }


                if (
                    Number.isNaN(bill) ||
                    bill < 0
                ) {

                    event.preventDefault();

                    alert(
                        "Please enter a valid Bill Amount."
                    );

                    if (billAmount) {
                        billAmount.focus();
                    }

                }

            }
        );

    }


    /* =====================================================
       RECEIVED SUBMIT
    ====================================================== */

    if (receivedForm) {

        receivedForm.addEventListener(
            "submit",
            function (event) {

                syncDates();


                const date =
                    receivedDateInput
                        ? receivedDateInput.value.trim()
                        : "";


                const amount =
                    parseFloat(
                        amountReceivedInput
                            ? amountReceivedInput.value
                            : ""
                    );


                if (!isValidDmy(date)) {

                    event.preventDefault();

                    alert(
                        "Please enter received date in dd/mm/yyyy format. Example: 31/08/2026"
                    );

                    if (receivedDateInput) {
                        receivedDateInput.focus();
                    }

                    return;

                }


                if (
                    Number.isNaN(amount) ||
                    amount < 0
                ) {

                    event.preventDefault();

                    alert(
                        "Please enter a valid Amount Received."
                    );

                    if (amountReceivedInput) {
                        amountReceivedInput.focus();
                    }

                }

            }
        );

    }


    /* =====================================================
       DELETE BILL CONFIRMATION
    ====================================================== */

    document
        .querySelectorAll(".delete-entry-form")
        .forEach(function (form) {

            form.addEventListener(
                "submit",
                function (event) {

                    const row =
                        this.closest("tr");


                    const dateCell =
                        row
                            ? row.querySelector(
                                '[data-label="Date"]'
                            )
                            : null;


                    const date =
                        dateCell
                            ? dateCell.textContent.trim()
                            : "";


                    const message =
                        "Delete bill entry" +
                        (date
                            ? " of " + date
                            : "") +
                        "?\n\nThis cannot be undone.";


                    if (!window.confirm(message)) {
                        event.preventDefault();
                    }

                }
            );

        });


    /* =====================================================
       DELETE RECEIVED CONFIRMATION
    ====================================================== */

    document
        .querySelectorAll(".delete-received-form")
        .forEach(function (form) {

            form.addEventListener(
                "submit",
                function (event) {

                    const row =
                        this.closest("tr");


                    const dateCell =
                        row
                            ? row.querySelector(
                                '[data-label="Date"]'
                            )
                            : null;


                    const amountCell =
                        row
                            ? row.querySelector(
                                '[data-label="Amount Received"]'
                            )
                            : null;


                    const date =
                        dateCell
                            ? dateCell.textContent.trim()
                            : "";


                    const amount =
                        amountCell
                            ? amountCell.textContent.trim()
                            : "";


                    const message =
                        "Delete received amount?\n\n" +
                        "Date: " +
                        date +
                        "\nAmount: " +
                        amount;


                    if (!window.confirm(message)) {
                        event.preventDefault();
                    }

                }
            );

        });


    /* =====================================================
       INITIAL DATE
    ====================================================== */

    setToday();


})();
