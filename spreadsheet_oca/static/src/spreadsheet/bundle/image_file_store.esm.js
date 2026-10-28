export class ImageFileStore {
    constructor(resModel, resId, http, orm) {
        this.resModel = resModel;
        this.resId = resId;
        this.http = http;
        this.orm = orm;
    }

    async upload(file) {
        const route = "/web/binary/upload_attachment";
        const params = {
            ufile: [file],
            csrf_token: odoo.csrf_token,
            model: this.resModel,
            id: this.resId,
        };
        const fileData = JSON.parse(await this.http.post(route, params, "text"))[0];
        const [accessToken] = await this.orm.call(
            "ir.attachment",
            "generate_access_token",
            [fileData.id]
        );
        return `/web/image/${fileData.id}?access_token=${accessToken}`;
    }

    async delete(path) {
        const attachmentId = path.split("/").pop();
        if (Number.isNaN(attachmentId)) {
            throw new Error("Invalid path: " + path);
        }
        await this.orm.unlink("ir.attachment", [parseInt(attachmentId, 10)]);
    }
}
