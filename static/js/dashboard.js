(function () {
    "use strict";

    // =====================================================
    // DASHBOARD DATA
    // =====================================================

    const dataElement = document.getElementById("recoveryData");

    if (!dataElement) {
        return;
    }

    const selectedYear =
        dataElement.dataset.selectedYear || "";

    const currentYear =
        dataElement.dataset.currentYear || selectedYear;

    const logoutUrl =
        dataElement.dataset.logoutUrl || "/logout";

    const clearUrl =
        dataElement.dataset.clearUrl || "/clear-all";

    const dashboardUrl =
        dataElement.dataset.dashboardUrl || "/dashboard";

    const addYearUrl =
        dataElement.dataset.addYearUrl || "/add-year";

    const deleteYearUrl =
        dataElement.dataset.deleteYearUrl || "/delete-year";


    // =====================================================
    // POPUP ELEMENTS
    // =====================================================

    const popupOverlay =
        document.getElementById("popupOverlay");

    const popupTitle =
        document.getElementById("popupTitle");

    const popupMessage =
        document.getElementById("popupMessage");

    const popupIcon =
        document.getElementById("popupIcon");

    const popupButtons =
        document.getElementById("popupButtons");

    const popupCloseButton =
        document.getElementById("popupCloseButton");


    // =====================================================
    // CLOSE POPUP
    // =====================================================

    function closePopup() {
        if (!popupOverlay) {
            return;
        }

        popupOverlay.classList.remove("show");

        if (popupButtons) {
            popupButtons.innerHTML = "";
        }
    }


    // =====================================================
    // OPEN POPUP
    // =====================================================

    function openPopup(
        title,
        message,
        icon,
        buttons
    ) {
        if (
            !popupOverlay ||
            !popupTitle ||
            !popupMessage ||
            !popupIcon ||
            !popupButtons
        ) {
            return;
        }

        popupTitle.textContent = title;

        popupMessage.innerHTML =
            message || "";

        popupIcon.textContent =
            icon || "?";

        popupButtons.innerHTML = "";


        (buttons || []).forEach(
            function (item) {

                const button =
                    document.createElement("button");

                button.type = "button";

                button.textContent =
                    item.text || "OK";

                button.className =
                    "popup-button " +
                    (item.className || "");

                button.addEventListener(
                    "click",
                    async function () {

                        try {
                            await item.action();
                        } catch (error) {
                            console.error(error);
                        }

                    }
                );

                popupButtons.appendChild(button);
            }
        );


        popupOverlay.classList.add("show");
    }


    // =====================================================
    // POPUP CLOSE BUTTON
    // =====================================================

    if (popupCloseButton) {

        popupCloseButton.addEventListener(
            "click",
            closePopup
        );

    }


    // =====================================================
    // CLICK OUTSIDE POPUP
    // =====================================================

    if (popupOverlay) {

        popupOverlay.addEventListener(
            "click",
            function (event) {

                if (
                    event.target ===
                    popupOverlay
                ) {
                    closePopup();
                }

            }
        );

    }


    // =====================================================
    // ESCAPE HTML
    // =====================================================

    function escapeHtml(value) {

        const div =
            document.createElement("div");

        div.textContent =
            value == null
                ? ""
                : String(value);

        return div.innerHTML;
    }


    // =====================================================
    // POST REQUEST
    // =====================================================

    async function requestForm(
        url,
        values
    ) {

        const formData =
            new FormData();


        Object.keys(values || {}).forEach(
            function (key) {

                formData.append(
                    key,
                    values[key]
                );

            }
        );


        const response =
            await fetch(
                url,
                {
                    method: "POST",
                    body: formData,
                    headers: {
                        "X-Requested-With":
                            "XMLHttpRequest"
                    }
                }
            );


        let result = null;


        try {

            result =
                await response.json();

        } catch (error) {

            result = null;

        }


        if (!response.ok) {

            throw new Error(
                result &&
                result.message
                    ? result.message
                    : "Request failed."
            );

        }


        if (
            result &&
            result.success === false
        ) {

            throw new Error(
                result.message ||
                "Request failed."
            );

        }


        return result;
    }


    // =====================================================
    // DOWNLOAD FILE
    // =====================================================

    async function downloadFile(
        url,
        filename
    ) {

        const response =
            await fetch(url);


        if (!response.ok) {

            let message =
                "PDF could not be created.";

            try {

                const data =
                    await response.json();

                if (data.message) {
                    message =
                        data.message;
                }

            } catch (error) {
                // Ignore JSON error
            }

            throw new Error(message);
        }


        const blob =
            await response.blob();


        const blobUrl =
            URL.createObjectURL(blob);


        const link =
            document.createElement("a");


        link.href =
            blobUrl;

        link.download =
            filename;


        document.body.appendChild(link);

        link.click();

        link.remove();


        setTimeout(
            function () {

                URL.revokeObjectURL(
                    blobUrl
                );

            },
            1000
        );
    }


    // =====================================================
    // DASHBOARD BY YEAR
    // =====================================================

    function dashboardForYear(year) {

        if (!year) {
            return;
        }

        window.location.href =
            dashboardUrl +
            "?year=" +
            encodeURIComponent(year);
    }


    // =====================================================
    // COPY RECOVERY ID
    // =====================================================

    async function copyRecoveryId(
        recoveryId
    ) {

        if (!recoveryId) {
            return;
        }


        try {

            if (
                navigator.clipboard &&
                navigator.clipboard.writeText
            ) {

                await navigator.clipboard.writeText(
                    recoveryId
                );

                alert(
                    "Recovery ID copied."
                );

                return;
            }

        } catch (error) {
            console.error(error);
        }


        alert(
            "Recovery ID: " +
            recoveryId
        );
    }


    // =====================================================
    // SHOW RECOVERY ID
    // =====================================================

    function showRecoveryId(
        result,
        title,
        message
    ) {

        if (
            !result ||
            !result.recovery_id
        ) {

            alert(
                message ||
                "Operation completed."
            );

            return;
        }


        const recoveryId =
            result.recovery_id;


        openPopup(
            title ||
            "Recovery ID Created",

            (
                (message || "") +
                "<br><br>" +
                "Recovery ID:<br>" +
                "<span class='recovery-id'>" +
                escapeHtml(recoveryId) +
                "</span>"
            ),

            "🔐",

            [

                {
                    text: "Copy ID",

                    className:
                        "popup-primary",

                    action:
                        async function () {

                            await copyRecoveryId(
                                recoveryId
                            );
                        }
                },


                {
                    text: "Done",

                    className:
                        "popup-cancel",

                    action:
                        function () {

                            closePopup();

                            dashboardForYear(
                                result.year ||
                                selectedYear
                            );
                        }
                }

            ]
        );
    }


    // =====================================================
    // LOGOUT
    // =====================================================

    const logoutButton =
        document.getElementById(
            "logoutButton"
        );


    if (logoutButton) {

        logoutButton.addEventListener(
            "click",
            function () {

                openPopup(

                    "Logout",

                    "Are you sure you want to logout?",

                    "🚪",

                    [

                        {
                            text: "Cancel",

                            className:
                                "popup-cancel",

                            action:
                                closePopup
                        },


                        {
                            text: "Logout",

                            className:
                                "popup-danger",

                            action:
                                function () {

                                    window.location.href =
                                        logoutUrl;
                                }
                        }

                    ]
                );
            }
        );
    }


    // =====================================================
    // FINANCIAL YEAR PICKER
    // =====================================================

    const yearPicker =
        document.getElementById(
            "yearPicker"
        );


    const yearPickerButton =
        document.getElementById(
            "yearPickerButton"
        );


    const yearMenu =
        document.getElementById(
            "yearMenu"
        );


    if (
        yearPickerButton &&
        yearMenu
    ) {

        yearPickerButton.addEventListener(
            "click",
            function () {

                const isOpen =
                    yearMenu.classList.toggle(
                        "show"
                    );


                yearPickerButton.setAttribute(
                    "aria-expanded",
                    isOpen
                        ? "true"
                        : "false"
                );
            }
        );


        document.addEventListener(
            "click",
            function (event) {

                if (
                    yearPicker &&
                    !yearPicker.contains(
                        event.target
                    )
                ) {

                    yearMenu.classList.remove(
                        "show"
                    );


                    yearPickerButton.setAttribute(
                        "aria-expanded",
                        "false"
                    );
                }
            }
        );
    }


    // =====================================================
    // SELECT YEAR
    // =====================================================

    document
        .querySelectorAll(
            ".year-select-button"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        dashboardForYear(
                            this.dataset.year
                        );
                    }
                );
            }
        );


    // =====================================================
    // ADD YEAR
    // =====================================================

    const addYearButton =
        document.getElementById(
            "addYearButton"
        );


    if (addYearButton) {

        addYearButton.addEventListener(
            "click",
            async function () {

                const entered =
                    window.prompt(
                        "Enter Financial Year\n\nExample:\n01/04/2027 - 31/03/2028"
                    );


                if (entered === null) {
                    return;
                }


                const value =
                    entered.trim();


                let normalized =
                    "";


                // -------------------------------------------------
                // DATE FORMAT
                // 01/04/2027 - 31/03/2028
                // -------------------------------------------------

                const labelMatch =
                    value.match(
                        /^01\/04\/(\d{4})\s*-\s*31\/03\/(\d{4})$/
                    );


                if (labelMatch) {

                    const startYear =
                        Number(
                            labelMatch[1]
                        );


                    const endYear =
                        Number(
                            labelMatch[2]
                        );


                    if (
                        endYear ===
                        startYear + 1
                    ) {

                        normalized =
                            startYear +
                            "-" +
                            String(
                                endYear
                            ).slice(-2);
                    }
                }


                // -------------------------------------------------
                // SHORT FORMAT
                // 2027-28
                // -------------------------------------------------

                if (!normalized) {

                    const shortMatch =
                        value.match(
                            /^(\d{4})\s*-\s*(\d{2}|\d{4})$/
                        );


                    if (shortMatch) {

                        const startYear =
                            Number(
                                shortMatch[1]
                            );


                        const endText =
                            shortMatch[2];


                        const endYear =
                            endText.length === 2
                                ? Number(
                                    String(
                                        startYear
                                    ).slice(0, 2) +
                                    endText
                                )
                                : Number(
                                    endText
                                );


                        if (
                            endYear ===
                            startYear + 1
                        ) {

                            normalized =
                                startYear +
                                "-" +
                                String(
                                    endYear
                                ).slice(-2);
                        }
                    }
                }


                // -------------------------------------------------
                // INVALID
                // -------------------------------------------------

                if (!normalized) {

                    alert(
                        "Please enter like:\n\n01/04/2027 - 31/03/2028"
                    );

                    return;
                }


                // -------------------------------------------------
                // SEND TO FLASK
                // -------------------------------------------------

                try {

                    const result =
                        await requestForm(
                            addYearUrl,
                            {
                                financial_year:
                                    normalized
                            }
                        );


                    openPopup(

                        "Financial Year Added",

                        "Financial Year:<br><strong>" +
                        escapeHtml(
                            result.label ||
                            (
                                "01/04/" +
                                normalized.slice(0, 4) +
                                " - 31/03/" +
                                (
                                    Number(
                                        normalized.slice(0, 4)
                                    ) + 1
                                )
                            )
                        ) +
                        "</strong><br><br>" +
                        "Financial year added successfully.",

                        "📅",

                        [

                            {
                                text: "OK",

                                className:
                                    "popup-primary",

                                action:
                                    function () {

                                        closePopup();

                                        dashboardForYear(
                                            result.year ||
                                            normalized
                                        );
                                    }
                            }

                        ]
                    );

                } catch (error) {

                    alert(
                        error.message ||
                        "Unable to add financial year."
                    );
                }
            }
        );
    }


    // =====================================================
    // DELETE FINANCIAL YEAR
    // =====================================================

    document
        .querySelectorAll(
            ".js-delete-year"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function (event) {

                        event.stopPropagation();


                        const year =
                            this.dataset.year;


                        if (!year) {
                            return;
                        }


                        if (
                            year ===
                            currentYear
                        ) {

                            alert(
                                "Current financial year cannot be deleted."
                            );

                            return;
                        }


                        const displayYear =
                            formatFinancialYear(
                                year
                            );


                        openPopup(

                            "Delete Financial Year?",

                            "Delete <strong>" +
                            escapeHtml(
                                displayYear
                            ) +
                            "</strong> and all its data?",

                            "🗑️",

                            [

                                {
                                    text: "Cancel",

                                    className:
                                        "popup-cancel",

                                    action:
                                        closePopup
                                },


                                {
                                    text: "Delete Year",

                                    className:
                                        "popup-danger",

                                    action:
                                        async function () {

                                        try {

                                            const result =
                                                await requestForm(
                                                    deleteYearUrl,
                                                    {
                                                        year:
                                                            year
                                                    }
                                                );


                                            showRecoveryId(

                                                result,

                                                "Financial Year Deleted",

                                                "The financial year and its data were deleted."
                                            );

                                        } catch (error) {

                                            alert(
                                                error.message ||
                                                "Unable to delete financial year."
                                            );

                                            closePopup();
                                        }
                                    }
                                }

                            ]
                        );
                    }
                );
            }
        );


    // =====================================================
    // FORMAT FINANCIAL YEAR
    // =====================================================

    function formatFinancialYear(
        year
    ) {

        if (!year) {
            return "";
        }


        const match =
            String(year).match(
                /^(\d{4})-(\d{2})$/
            );


        if (!match) {
            return year;
        }


        const startYear =
            Number(
                match[1]
            );


        const endYear =
            startYear + 1;


        return (
            "01/04/" +
            startYear +
            " - 31/03/" +
            endYear
        );
    }


    // =====================================================
    // SINGLE SAVE
    // =====================================================

    document
        .querySelectorAll(
            ".js-save-file"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        const businessId =
                            this.dataset.businessId;


                        const businessName =
                            this.dataset.businessName ||
                            "Business";


                        openPopup(

                            "Save PDF",

                            "Save the complete statement for <strong>" +
                            escapeHtml(
                                businessName
                            ) +
                            "</strong>?<br><br>" +
                            "The PDF includes Bill Entries, Amount Received, Close Amount and Net Amount.",

                            "📄",

                            [

                                {
                                    text: "Cancel",

                                    className:
                                        "popup-cancel",

                                    action:
                                        closePopup
                                },


                                {
                                    text: "Save",

                                    className:
                                        "popup-primary",

                                    action:
                                        async function () {

                                        closePopup();


                                        try {

                                            await downloadFile(

                                                "/save-file/" +
                                                businessId +
                                                "?year=" +
                                                encodeURIComponent(
                                                    selectedYear
                                                ),

                                                sanitizeFilename(
                                                    businessName
                                                ) +
                                                "_" +
                                                selectedYear +
                                                ".pdf"
                                            );

                                        } catch (error) {

                                            alert(
                                                error.message ||
                                                "PDF could not be created."
                                            );
                                        }
                                    }
                                }

                            ]
                        );
                    }
                );
            }
        );


    // =====================================================
    // SINGLE VIEW
    // =====================================================

    document
        .querySelectorAll(
            ".js-view-file"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        const businessId =
                            this.dataset.businessId;


                        window.open(

                            "/view-file/" +
                            businessId +
                            "?year=" +
                            encodeURIComponent(
                                selectedYear
                            ),

                            "_blank"
                        );
                    }
                );
            }
        );


    // =====================================================
    // VIEW ALL
    // =====================================================

    const viewAllButton =
        document.getElementById(
            "viewAllButton"
        );


    if (viewAllButton) {

        viewAllButton.addEventListener(
            "click",
            function () {

                window.open(

                    "/view-all?year=" +
                    encodeURIComponent(
                        selectedYear
                    ),

                    "_blank"
                );
            }
        );
    }


    // =====================================================
    // SHARE PDF
    // =====================================================

    document
        .querySelectorAll(
            ".js-share-file"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    async function () {

                        const businessId =
                            this.dataset.businessId;


                        const businessName =
                            this.dataset.businessName ||
                            "Business";


                        openPopup(

                            "Share",

                            "Preparing PDF for <strong>" +
                            escapeHtml(
                                businessName
                            ) +
                            "</strong>...",

                            "📤",

                            [

                                {
                                    text: "Please wait",

                                    className:
                                        "popup-disabled",

                                    action:
                                        function () {}
                                }

                            ]
                        );


                        try {

                            const response =
                                await fetch(

                                    "/share-file/" +
                                    businessId +
                                    "?year=" +
                                    encodeURIComponent(
                                        selectedYear
                                    )
                                );


                            if (!response.ok) {

                                throw new Error(
                                    "PDF generation failed."
                                );
                            }


                            const blob =
                                await response.blob();


                            const filename =
                                sanitizeFilename(
                                    businessName
                                ) +
                                "_" +
                                selectedYear +
                                ".pdf";


                            const file =
                                new File(
                                    [blob],
                                    filename,
                                    {
                                        type:
                                            "application/pdf"
                                    }
                                );


                            closePopup();


                            if (
                                navigator.share &&
                                navigator.canShare &&
                                navigator.canShare(
                                    {
                                        files:
                                            [file]
                                    }
                                )
                            ) {

                                await navigator.share(
                                    {
                                        title:
                                            businessName +
                                            " PDF",

                                        text:
                                            businessName +
                                            " Business Statement " +
                                            selectedYear,

                                        files:
                                            [file]
                                    }
                                );


                                return;
                            }


                            alert(
                                "Direct file sharing is not supported by this browser. Use Save and share the saved PDF through WhatsApp."
                            );

                        } catch (error) {

                            closePopup();


                            if (
                                error &&
                                error.name ===
                                "AbortError"
                            ) {
                                return;
                            }


                            alert(
                                error.message ||
                                "Sharing failed."
                            );
                        }
                    }
                );
            }
        );


    // =====================================================
    // DELETE BUSINESS
    // =====================================================

    document
        .querySelectorAll(
            ".js-delete-business"
        )
        .forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        const businessId =
                            this.dataset.businessId;


                        const businessName =
                            this.dataset.businessName ||
                            "this name";


                        openPopup(

                            "Delete Name?",

                            "Do you want to delete the name <strong>" +
                            escapeHtml(
                                businessName
                            ) +
                            "</strong>?",

                            "🗑️",

                            [

                                {
                                    text: "No",

                                    className:
                                        "popup-cancel",

                                    action:
                                        function () {

                                            closePopup();


                                            openDeleteDataPopup(

                                                businessId,

                                                businessName
                                            );
                                        }
                                },


                                {
                                    text: "Yes",

                                    className:
                                        "popup-danger",

                                    action:
                                        async function () {

                                        try {

                                            const result =
                                                await requestForm(

                                                    "/delete-business/" +
                                                    businessId,

                                                    {
                                                        mode:
                                                            "name-only",

                                                        year:
                                                            selectedYear
                                                    }
                                                );


                                            closePopup();


                                            openNameDeletedPopup(

                                                businessId,

                                                businessName,

                                                result
                                            );

                                        } catch (error) {

                                            alert(
                                                error.message ||
                                                "Unable to delete name."
                                            );

                                            closePopup();
                                        }
                                    }
                                }

                            ]
                        );
                    }
                );
            }
        );


    // =====================================================
    // NAME DELETED POPUP
    // =====================================================

    function openNameDeletedPopup(

        businessId,

        businessName,

        result

    ) {

        const recoveryId =
            result &&
            result.recovery_id
                ? result.recovery_id
                : "";


        openPopup(

            "Name Deleted",

            "The name <strong>" +
            escapeHtml(
                businessName
            ) +
            "</strong> is now hidden.<br><br>" +
            "Recovery ID:<br>" +
            "<span class='recovery-id'>" +
            escapeHtml(
                recoveryId
            ) +
            "</span>",

            "🔐",

            [

                {
                    text: "Copy ID",

                    className:
                        "popup-primary",

                    action:
                        async function () {

                            await copyRecoveryId(
                                recoveryId
                            );
                        }
                },


                {
                    text: "Keep Data",

                    className:
                        "popup-cancel",

                    action:
                        function () {

                            closePopup();

                            dashboardForYear(
                                result.year ||
                                selectedYear
                            );
                        }
                },


                {
                    text: "Delete Data Too",

                    className:
                        "popup-danger",

                    action:
                        function () {

                            closePopup();


                            openPopup(

                                "Delete Data Too?",

                                "Permanently delete all data for <strong>" +
                                escapeHtml(
                                    businessName
                                ) +
                                "</strong>?",

                                "⚠️",

                                [

                                    {
                                        text: "No",

                                        className:
                                            "popup-cancel",

                                        action:
                                            function () {

                                                closePopup();

                                                dashboardForYear(
                                                    result.year ||
                                                    selectedYear
                                                );
                                            }
                                    },


                                    {
                                        text: "Yes, Delete Data",

                                        className:
                                            "popup-danger",

                                        action:
                                            async function () {

                                            try {

                                                const finalResult =
                                                    await requestForm(

                                                        "/delete-business/" +
                                                        businessId,

                                                        {
                                                            mode:
                                                                "all",

                                                            year:
                                                                selectedYear
                                                        }
                                                    );


                                                showRecoveryId(

                                                    finalResult,

                                                    "Name + Data Deleted",

                                                    "The business name and its data were deleted."
                                                );

                                            } catch (error) {

                                                alert(
                                                    error.message ||
                                                    "Unable to delete data."
                                                );
                                            }
                                        }
                                    }

                                ]
                            );
                        }
                }

            ]
        );
    }


    // =====================================================
    // DELETE DATA ONLY
    // =====================================================

    function openDeleteDataPopup(

        businessId,

        businessName

    ) {

        openPopup(

            "Delete Data?",

            "Do you want to permanently delete the selected financial year's data for <strong>" +
            escapeHtml(
                businessName
            ) +
            "</strong>?",

            "⚠️",

            [

                {
                    text: "No",

                    className:
                        "popup-cancel",

                    action:
                        closePopup
                },


                {
                    text: "Yes, Delete Data",

                    className:
                        "popup-danger",

                    action:
                        async function () {

                        try {

                            const result =
                                await requestForm(

                                    "/delete-business/" +
                                    businessId,

                                    {
                                        mode:
                                            "data-only",

                                        year:
                                            selectedYear
                                    }
                                );


                            showRecoveryId(

                                result,

                                "Data Deleted",

                                "The selected financial year's data was deleted."
                            );

                        } catch (error) {

                            alert(
                                error.message ||
                                "Unable to delete data."
                            );
                        }
                    }
                }

            ]
        );
    }


    // =====================================================
    // SAVE ALL
    // =====================================================

    const saveAllButton =
        document.getElementById(
            "saveAllButton"
        );


    if (saveAllButton) {

        saveAllButton.addEventListener(
            "click",
            function () {

                openPopup(

                    "Save All",

                    "Create <strong>one PDF</strong> for <strong>" +
                    escapeHtml(
                        formatFinancialYear(
                            selectedYear
                        )
                    ) +
                    "</strong>?<br><br>" +
                    "The PDF will contain the Index first, then each business on a new page.",

                    "📄",

                    [

                        {
                            text: "Cancel",

                            className:
                                "popup-cancel",

                            action:
                                closePopup
                        },


                        {
                            text: "Save All",

                            className:
                                "popup-primary",

                            action:
                                async function () {

                                closePopup();


                                try {

                                    await downloadFile(

                                        "/save-all?year=" +
                                        encodeURIComponent(
                                            selectedYear
                                        ),

                                        "Business_Manager_" +
                                        selectedYear +
                                        ".pdf"
                                    );

                                } catch (error) {

                                    alert(
                                        error.message ||
                                        "PDF could not be created."
                                    );
                                }
                            }
                        }

                    ]
                );
            }
        );
    }


    // =====================================================
    // VIEW ALL
    // =====================================================

    // This also supports HTML where View All
    // button is added dynamically.

    document.addEventListener(
        "click",
        function (event) {

            const button =
                event.target.closest(
                    "#viewAllButton"
                );


            if (!button) {
                return;
            }


            window.open(

                "/view-all?year=" +
                encodeURIComponent(
                    selectedYear
                ),

                "_blank"
            );
        }
    );


    // =====================================================
    // CHECK WHETHER CLEAR ALL HAS DATA
    // =====================================================

    function hasClearableData() {

        const rows =
            document.querySelectorAll(
                "tbody tr"
            );


        // -------------------------------------------------
        // If at least one business exists,
        // there may be data.
        // Backend performs final safety check.
        // -------------------------------------------------

        let hasBusiness =
            false;


        rows.forEach(
            function (row) {

                const deleteButton =
                    row.querySelector(
                        ".js-delete-business"
                    );


                if (deleteButton) {
                    hasBusiness = true;
                }
            }
        );


        // -------------------------------------------------
        // Read visible amounts
        // -------------------------------------------------

        const moneyCells =
            document.querySelectorAll(
                ".money-cell"
            );


        let hasAmount =
            false;


        moneyCells.forEach(
            function (cell) {

                const text =
                    cell.textContent
                        .replace(
                            /[₹,\sRs.]/g,
                            ""
                        )
                        .trim();


                const amount =
                    Number(
                        text
                    );


                if (
                    !isNaN(amount) &&
                    amount !== 0
                ) {

                    hasAmount = true;
                }
            }
        );


        return (
            hasBusiness ||
            hasAmount
        );
    }


    // =====================================================
    // CLEAR ALL
    // =====================================================

    const clearButton =
        document.getElementById(
            "clearButton"
        );


    if (clearButton) {

        clearButton.addEventListener(
            "click",
            function () {

                // -------------------------------------------------
                // NO DATA = NO POPUP
                // -------------------------------------------------

                if (
                    !hasClearableData()
                ) {

                    return;
                }


                // -------------------------------------------------
                // FIRST POPUP
                // -------------------------------------------------

                openPopup(

                    "Clear All Data",

                    "Clear all saved business data and financial years?",

                    "⚠️",

                    [

                        {
                            text: "Cancel",

                            className:
                                "popup-cancel",

                            action:
                                closePopup
                        },


                        {
                            text: "Save All & Clear",

                            className:
                                "popup-warning",

                            action:
                                async function () {

                                closePopup();


                                try {

                                    // -------------------------------------------------
                                    // FIRST SAVE CURRENT INDEX PDF
                                    // -------------------------------------------------

                                    await downloadFile(

                                        "/save-all?year=" +
                                        encodeURIComponent(
                                            selectedYear
                                        ),

                                        "Business_Manager_" +
                                        selectedYear +
                                        ".pdf"
                                    );


                                    // -------------------------------------------------
                                    // THEN CLEAR EVERYTHING
                                    // -------------------------------------------------

                                    const result =
                                        await requestForm(

                                            clearUrl,

                                            {
                                                year:
                                                    selectedYear
                                            }
                                        );


                                    showRecoveryId(

                                        result,

                                        "All Data Cleared",

                                        "All saved data was cleared."
                                    );

                                } catch (error) {

                                    alert(
                                        error.message ||
                                        "Unable to clear data."
                                    );
                                }
                            }
                        },


                        {
                            text: "Clear Without Save",

                            className:
                                "popup-danger",

                            action:
                                function () {

                                    closePopup();


                                    openPopup(

                                        "Final Confirmation",

                                        "Are you sure you want to clear all saved business data and financial years?",

                                        "⚠️",

                                        [

                                            {
                                                text: "No",

                                                className:
                                                    "popup-cancel",

                                                action:
                                                    closePopup
                                            },


                                            {
                                                text: "Yes, Clear",

                                                className:
                                                    "popup-danger",

                                                action:
                                                    async function () {

                                                    try {

                                                        const result =
                                                            await requestForm(

                                                                clearUrl,

                                                                {
                                                                    year:
                                                                        selectedYear
                                                                }
                                                            );


                                                        showRecoveryId(

                                                            result,

                                                            "All Data Cleared",

                                                            "All saved data was cleared."
                                                        );

                                                    } catch (error) {

                                                        alert(
                                                            error.message ||
                                                            "Unable to clear data."
                                                        );

                                                        closePopup();
                                                    }
                                                }
                                            }

                                        ]
                                    );
                                }
                        }

                    ]
                );
            }
        );
    }


    // =====================================================
    // SEARCH
    // =====================================================

    const searchForm =
        document.getElementById(
            "searchForm"
        );


    const searchInput =
        document.getElementById(
            "searchInput"
        );


    if (
        searchForm &&
        searchInput
    ) {

        searchForm.addEventListener(
            "submit",
            function (event) {

                const value =
                    searchInput.value.trim();


                if (!value) {

                    event.preventDefault();

                    dashboardForYear(
                        selectedYear
                    );

                    return;
                }


                // REC-xxxxxxxx stays in normal search.
                // Flask backend restores matching backup.
            }
        );
    }


    // =====================================================
    // FILE NAME CLEANER
    // =====================================================

    function sanitizeFilename(
        name
    ) {

        return String(name || "Business")
            .replace(
                /[<>:"/\\|?*]+/g,
                "_"
            )
            .trim();
    }


    // =====================================================
    // AUTOMATIC LIVE FINANCIAL YEAR
    // =====================================================

    /*
        Important:

        JavaScript cannot create the financial year
        directly inside SQLite.

        The Flask /dashboard route must automatically
        ensure today's financial year exists.

        Example:

        01/04/2026 -> 2026-27
        01/04/2027 -> 2027-28
        01/04/2028 -> 2028-29

        Therefore, whenever the dashboard opens,
        Flask should create the current FY automatically.
    */


    // -----------------------------------------------------
    // Optional refresh check
    // -----------------------------------------------------

    // This reloads the dashboard when the browser has
    // been kept open around April 1.
    // It does not create the year itself.
    // Flask creates it when dashboard is requested.

    function checkLiveFinancialYear() {

        const now =
            new Date();


        const month =
            now.getMonth() + 1;


        const day =
            now.getDate();


        if (
            month === 4 &&
            day === 1
        ) {

            const currentStartYear =
                now.getFullYear();


            const expectedYear =
                currentStartYear +
                "-" +
                String(
                    currentStartYear + 1
                ).slice(-2);


            if (
                selectedYear !==
                expectedYear
            ) {

                window.location.href =
                    dashboardUrl +
                    "?year=" +
                    encodeURIComponent(
                        expectedYear
                    );
            }
        }
    }


    checkLiveFinancialYear();


})();
