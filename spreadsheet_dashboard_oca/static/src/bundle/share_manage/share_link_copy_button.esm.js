import {CopyButton} from "@web/core/copy_button/copy_button";
import {browser} from "@web/core/browser/browser";

/**
 * Copy button with a fallback for non-secure contexts.
 *
 * `navigator.clipboard` is only exposed on secure origins (HTTPS or
 * localhost), so the standard button silently does nothing when Odoo is
 * served over plain HTTP, as runboat does. In that case we copy through the
 * legacy `document.execCommand("copy")` API instead.
 */
export class ShareLinkCopyButton extends CopyButton {
    async onClick() {
        if (browser.navigator.clipboard?.writeText) {
            return super.onClick();
        }
        const content =
            typeof this.props.content === "function"
                ? this.props.content()
                : this.props.content;
        if (this._copyWithLegacyApi(content)) {
            this.showTooltip();
        } else {
            browser.console.warn("Could not copy the share link to the clipboard.");
        }
    }

    _copyWithLegacyApi(value) {
        const textarea = browser.document.createElement("textarea");
        textarea.value = value;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        browser.document.body.appendChild(textarea);
        textarea.select();
        let copied = false;
        try {
            copied = browser.document.execCommand("copy");
        } catch {
            copied = false;
        }
        textarea.remove();
        return copied;
    }
}
