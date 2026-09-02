(function () {
    "use strict";

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
    // POPUP
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


    function closePopup() {
        if (!popupOverlay) {
            return;
        }

        popupOverlay.classList.remove("show");

        if (popupButtons) {
            popupButtons.innerHTML = "";
        }
    }


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
        popupMessage.innerHTML = message;
        popupIcon.textContent = icon;
        popupButtons.innerHTML = "";

        buttons.forEach(function (item) {
            const button =
                document.createElement("button");

            button.type = "button";
            button.textContent = item.text;
            button.className =
                "popup-button " +
                (item.className || "");

            button.addEventListener(
                "click",
                item.action
            );

            popupButtons.appendChild(button);
        });

        popupOverlay.classList.add("show");
    }


    if (popupCloseButton) {
        popupCloseButton.addEventListener(
            "click",
            closePopup
        );
    }


    if (popupOverlay) {
        popupOverlay.addEventListener(
            "click",
            function (event) {
                if (event.target === popupOverlay) {
                    closePopup();
                }
            }
        );
    }


    // =====================================================
    // HELPERS
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
                    body: formData
                }
            );

        let result = null;

        try {
            result = await response.json();
        } catch (error) {
            result = null;
        }

        if (!response.ok) {
            throw new Error(
                result && result.message
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


    async function downloadFile(
        url,
        filename
    ) {
        const response =
            await fetch(url);

        if (!response.ok) {
            throw new Error(
                "PDF could not be created."
            );
        }

        const blob =
            await response.blob();

        const blobUrl =
            URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        link.href = blobUrl;
        link.download = filename;

        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(
            function () {
                URL.revokeObjectURL(blobUrl);
            },
            1000
        );
    }


    function dashboardForYear(year) {
        window.location.href =
            dashboardUrl +
            "?year=" +
            encodeURIComponent(year);
    }


    function showRecoveryId(
        result,
        title,
        message
    ) {
        if (
            !result ||
            !result.recovery_id
        ) {
            return;
        }

        openPopup(
            title || "Recovery ID Created",
            (message || "") +
            "<br><br>" +
            "Recovery ID:<br>" +
            "<span class='recovery-id'>" +
            escapeHtml(result.recovery_id) +
            "</span><br><br>" +
            "Paste this ID into the normal Search box to restore the deleted data.",
            "🔐",
            [
                {
                    text: "Copy ID",
                    className: "popup-primary",
                    action: async function () {
                        try {
                            await navigator.clipboard.writeText(
                                result.recovery_id
                            );

                            alert(
                                "Recovery ID copied."
                            );
                        } catch (error) {
                            alert(
                                "Recovery ID: " +
                                result.recovery_id
                            );
                        }
                    }
                },
                {
                    text: "Done",
                    className: "popup-cancel",
                    action: function () {
                        closePopup();
                        dashboardForYear(
                            result.year || selectedYear
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
        document.getElementById("logoutButton");

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
                            className: "popup-cancel",
                            action: closePopup
                        },
                        {
                            text: "Logout",
                            className: "popup-danger",
                            action: function () {
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
        document.getElementById("yearPicker");

    const yearPickerButton =
        document.getElementById(
            "yearPickerButton"
        );

    const yearMenu =
        document.getElementById("yearMenu");


    if (
        yearPickerButton &&
        yearMenu
    ) {
        yearPickerButton.addEventListener(
            "click",
            function () {
                const isOpen =
                    yearMenu.classList.toggle("show");

                yearPickerButton.setAttribute(
                    "aria-expanded",
                    isOpen ? "true" : "false"
                );
            }
        );

        document.addEventListener(
            "click",
            function (event) {
                if (
                    yearPicker &&
                    !yearPicker.contains(event.target)
                ) {
                    yearMenu.classList.remove("show");

                    yearPickerButton.setAttribute(
                        "aria-expanded",
                        "false"
                    );
                }
            }
        );
    }


    document
        .querySelectorAll(".year-select-button")
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
                const entered = window.prompt(
                    "Enter Financial Year\nExample: 01/04/2027 - 31/03/2028"
                );

                if (entered === null) {
                    return;
                }

                const value = entered.trim();
                let normalized = "";

                const labelMatch = value.match(
                    /^01\/04\/(\d{4})\s*-\s*31\/03\/(\d{4})$/
                );

                if (labelMatch) {
                    const startYear = Number(labelMatch[1]);
                    const endYear = Number(labelMatch[2]);

                    if (endYear === startYear + 1) {
                        normalized =
                            startYear + "-" +
                            String(endYear).slice(-2);
                    }
                }

                if (!normalized) {
                    const shortMatch = value.match(
                        /^(\d{4})\s*-\s*(\d{2}|\d{4})$/
                    );

                    if (shortMatch) {
                        const startYear = Number(shortMatch[1]);
                        const endText = shortMatch[2];
                        const endYear =
                            endText.length === 2
                                ? Number(String(startYear).slice(0, 2) + endText)
                                : Number(endText);

                        if (endYear === startYear + 1) {
                            normalized =
                                startYear + "-" +
                                String(endYear).slice(-2);
                        }
                    }
                }

                if (!normalized) {
                    alert(
                        "Please enter like:\n01/04/2027 - 31/03/2028"
                    );
                    return;
                }

                try {
                    const result = await requestForm(
                        addYearUrl,
                        { financial_year: normalized }
                    );

                    openPopup(
                        "Financial Year Added",
                        "Financial Year:<br><strong>" +
                        escapeHtml(result.label || normalized) +
                        "</strong><br><br>Financial year added successfully.",
                        "📅",
                        [
                            {
                                text: "OK",
                                className: "popup-primary",
                                action: function () {
                                    closePopup();
                                    dashboardForYear(result.year || normalized);
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
        .querySelectorAll(".js-delete-year")
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

                        if (year === currentYear) {
                            alert(
                                "Current financial year cannot be deleted."
                            );
                            return;
                        }

                        openPopup(
                            "Delete Financial Year?",
                            "Delete <strong>" +
                            escapeHtml(year) +
                            "</strong> and all of its bills, received amounts and close amounts?<br><br>" +
                            "A Recovery ID will be created before deletion.",
                            "🗑️",
                            [
                                {
                                    text: "Cancel",
                                    className: "popup-cancel",
                                    action: closePopup
                                },
                                {
                                    text: "Delete Year",
                                    className: "popup-danger",
                                    action: async function () {
                                        try {
                                            const result =
                                                await requestForm(
                                                    deleteYearUrl,
                                                    {
                                                        year: year
                                                    }
                                                );

                                            showRecoveryId(
                                                result,
                                                "Financial Year Deleted",
                                                "The financial year and its data were deleted safely."
                                            );
                                        } catch (error) {
                                            alert(
                                                error.message ||
                                                "Unable to delete financial year."
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
    // SINGLE SAVE
    // =====================================================

    document
        .querySelectorAll(".js-save-file")
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
                            escapeHtml(businessName) +
                            "</strong>?<br><br>" +
                            "The PDF includes Bill Entries, Amount Received, Close Amount and Net Amount.",
                            "📄",
                            [
                                {
                                    text: "Cancel",
                                    className: "popup-cancel",
                                    action: closePopup
                                },
                                {
                                    text: "Save",
                                    className: "popup-primary",
                                    action: async function () {
                                        closePopup();

                                        try {
                                            await downloadFile(
                                                "/save-file/" +
                                                businessId +
                                                "?year=" +
                                                encodeURIComponent(
                                                    selectedYear
                                                ),
                                                businessName +
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
        .querySelectorAll(".js-view-file")
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
    // SHARE
    // =====================================================

    document
        .querySelectorAll(".js-share-file")
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
                            escapeHtml(businessName) +
                            "</strong>...",
                            "📤",
                            [
                                {
                                    text: "Please wait",
                                    className: "popup-disabled",
                                    action: function () {}
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
                                businessName +
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
                                navigator.canShare({
                                    files: [file]
                                })
                            ) {
                                await navigator.share({
                                    title:
                                        businessName +
                                        " PDF",
                                    text:
                                        businessName +
                                        " Business Statement " +
                                        selectedYear,
                                    files: [file]
                                });

                                return;
                            }

                            alert(
                                "Direct file sharing is not supported by this browser. " +
                                "Use Save and share the saved PDF through WhatsApp."
                            );
                        } catch (error) {
                            closePopup();

                            if (
                                error &&
                                error.name === "AbortError"
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
    // DELETE BUSINESS - TWO STEP + RECOVERY
    // =====================================================

    document
        .querySelectorAll(".js-delete-business")
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
                            escapeHtml(businessName) +
                            "</strong>?",
                            "🗑️",
                            [
                                {
                                    text: "No",
                                    className: "popup-cancel",
                                    action: function () {
                                        closePopup();

                                        openDeleteDataPopup(
                                            businessId,
                                            businessName,
                                            false
                                        );
                                    }
                                },
                                {
                                    text: "Yes",
                                    className: "popup-danger",
                                    action: async function () {
                                        try {
                                            const result =
                                                await requestForm(
                                                    "/delete-business/" +
                                                    businessId,
                                                    {
                                                        mode: "name-only",
                                                        year: selectedYear
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


    function openNameDeletedPopup(
        businessId,
        businessName,
        result
    ) {
        openPopup(
            "Name Deleted",
            "The name <strong>" +
            escapeHtml(businessName) +
            "</strong> is now hidden.<br><br>" +
            "Its data is still saved.<br><br>" +
            "Recovery ID:<br>" +
            "<span class='recovery-id'>" +
            escapeHtml(result.recovery_id) +
            "</span>",
            "🔐",
            [
                {
                    text: "Copy ID",
                    className: "popup-primary",
                    action: async function () {
                        try {
                            await navigator.clipboard.writeText(
                                result.recovery_id
                            );
                            alert("Recovery ID copied.");
                        } catch (error) {
                            alert(
                                "Recovery ID: " +
                                result.recovery_id
                            );
                        }
                    }
                },
                {
                    text: "Keep Data",
                    className: "popup-cancel",
                    action: function () {
                        closePopup();
                        dashboardForYear(
                            result.year || selectedYear
                        );
                    }
                },
                {
                    text: "Delete Data Too",
                    className: "popup-danger",
                    action: function () {
                        closePopup();

                        openPopup(
                            "Delete Data Too?",
                            "Permanently delete all data for <strong>" +
                            escapeHtml(businessName) +
                            "</strong>?<br><br>" +
                            "A new Recovery ID will be created.",
                            "⚠️",
                            [
                                {
                                    text: "No",
                                    className: "popup-cancel",
                                    action: function () {
                                        closePopup();
                                        dashboardForYear(
                                            result.year || selectedYear
                                        );
                                    }
                                },
                                {
                                    text: "Yes, Delete Data",
                                    className: "popup-danger",
                                    action: async function () {
                                        try {
                                            const finalResult =
                                                await requestForm(
                                                    "/delete-business/" +
                                                    businessId,
                                                    {
                                                        mode: "all",
                                                        year: selectedYear
                                                    }
                                                );

                                            showRecoveryId(
                                                finalResult,
                                                "Name + Data Deleted",
                                                "The business name and all of its data were permanently removed."
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


    function openDeleteDataPopup(
        businessId,
        businessName,
        nameDeleted
    ) {
        openPopup(
            "Delete Data?",
            (
                "The name will remain in the list.<br><br>" +
                "Do you want to permanently delete the selected financial year's data for <strong>" +
                escapeHtml(businessName) +
                "</strong>?<br><br>" +
                "A Recovery ID will be created."
            ),
            "⚠️",
            [
                {
                    text: "No",
                    className: "popup-cancel",
                    action: closePopup
                },
                {
                    text: "Yes, Delete Data",
                    className: "popup-danger",
                    action: async function () {
                        try {
                            const result =
                                await requestForm(
                                    "/delete-business/" +
                                    businessId,
                                    {
                                        mode: "data-only",
                                        year: selectedYear
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
                    escapeHtml(selectedYear) +
                    "</strong>?<br><br>" +
                    "The PDF will contain the Index first, then each business on a new page.",
                    "📄",
                    [
                        {
                            text: "Cancel",
                            className: "popup-cancel",
                            action: closePopup
                        },
                        {
                            text: "Save All",
                            className: "popup-primary",
                            action: async function () {
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
    // CLEAR ALL YEARS
    // =====================================================

    const clearButton =
        document.getElementById(
            "clearButton"
        );

    if (clearButton) {
        clearButton.addEventListener(
            "click",
            function () {
                openPopup(
                    "Clear All Data",
                    "This will clear <strong>all bills, received amounts and close amounts for all financial years</strong>.<br><br>" +
                    "Business names and financial years will remain.<br><br>" +
                    "A Recovery ID will be created before clearing.",
                    "⚠️",
                    [
                        {
                            text: "Cancel",
                            className: "popup-cancel",
                            action: closePopup
                        },
                        {
                            text: "Save All & Clear",
                            className: "popup-warning",
                            action: async function () {
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

                                    const result =
                                        await requestForm(
                                            clearUrl,
                                            {
                                                year: selectedYear
                                            }
                                        );

                                    showRecoveryId(
                                        result,
                                        "All Data Cleared",
                                        "All financial-year data was cleared. Business names remain."
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
                            className: "popup-danger",
                            action: function () {
                                closePopup();

                                openPopup(
                                    "Final Confirmation",
                                    "Are you sure you want to clear <strong>all financial-year data</strong>?<br><br>" +
                                    "Business names will remain and a Recovery ID will be generated.",
                                    "⚠️",
                                    [
                                        {
                                            text: "No",
                                            className: "popup-cancel",
                                            action: closePopup
                                        },
                                        {
                                            text: "Yes, Clear",
                                            className: "popup-danger",
                                            action: async function () {
                                                try {
                                                    const result =
                                                        await requestForm(
                                                            clearUrl,
                                                            {
                                                                year: selectedYear
                                                            }
                                                        );

                                                    showRecoveryId(
                                                        result,
                                                        "All Data Cleared",
                                                        "All financial-year data was cleared."
                                                    );
                                                } catch (error) {
                                                    alert(
                                                        error.message ||
                                                        "Unable to clear data."
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

                // REC-... stays in the normal search box.
                // Flask automatically restores it.
            }
        );
    }

})();
