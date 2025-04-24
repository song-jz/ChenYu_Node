import { ComfyApp, app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
export async function loadResource(t, e = "") {
  if (!document.querySelector(`script[src="${t}"]`)) {
    const e = document.createElement("script");
    (e.src = t), document.head.appendChild(e);
    try {
      await new Promise((o, a) => {
        (e.onload = o),
          (e.onerror = () => a(new Error(`Failed to load script: ${t}`)));
      });
    } catch (t) {}
  }
  if (e) {
    if (!document.querySelector(`link[href="${e}"]`)) {
      const t = document.createElement("link");
      (t.rel = "stylesheet"), (t.href = e), document.head.appendChild(t);
      try {
        await new Promise((o, a) => {
          (t.onload = o),
            (t.onerror = () => a(new Error(`Failed to load stylesheet: ${e}`)));
        });
      } catch (t) {}
    }
  }
}
let toastHasLoaded = !1;
async function loadToast() {
  if (!toastHasLoaded) {
    const t = "https://cdn.jsdelivr.net/npm/toastify-js",
      e = "https://cdn.jsdelivr.net/npm/toastify-js/src/toastify.min.css";
    await loadResource(t, e), (toastHasLoaded = !0);
  }
}
export async function showToast(t, e = "info", o = 3e3) {
  await loadToast(),
    "info" == e
      ? Toastify({
          text: t,
          duration: o,
          close: !1,
          gravity: "top",
          position: "center",
          backgroundColor: "#3498db",
          stopOnFocus: !1,
        }).showToast()
      : "error" == e
      ? Toastify({
          text: t,
          duration: o,
          close: !0,
          gravity: "top",
          position: "center",
          backgroundColor: "#FF4444",
          stopOnFocus: !0,
        }).showToast()
      : "warning" == e &&
        Toastify({
          text: t,
          duration: o,
          close: !0,
          gravity: "top",
          position: "center",
          backgroundColor: "#FFA500",
          stopOnFocus: !0,
        }).showToast();
}
let messageBoxHasLoaded = !1;
export async function loadMessageBox() {
  messageBoxHasLoaded ||
    (await loadResource(
      "https://cdn.jsdelivr.net/npm/sweetalert2@11",
      "https://cdn.jsdelivr.net/npm/@sweetalert2/theme-bootstrap-4/bootstrap-4.css"
    ),
    (messageBoxHasLoaded = !0));
}
async function serverShowMessageBox(t, e) {
  await loadMessageBox();
  const o = { ...t, heightAuto: !1 };
  try {
    const t = await Swal.fire(o);
    api.fetchApi("/cryptocat/message", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `id=${e}&message=${t.isConfirmed ? "1" : "0"}`,
    });
  } catch (t) {
    api.fetchApi("/cryptocat/message", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `id=${e}&message=0`,
    });
  }
  window.addEventListener(
    "beforeunload",
    function () {
      fetch("/cryptocat/message", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `id=${e}&message=0`,
        keepalive: !0,
      });
    },
    { once: !0 }
  );
}
api.addEventListener("cryptocat_toast", (t) => {
  showToast(t.detail.content, t.detail.type, t.detail.duration);
}),
  api.addEventListener("cryptocat_dialog", (t) => {
    serverShowMessageBox(JSON.parse(t.detail.json_content), t.detail.id);
  });
export async function showMessageBox(t, e, o) {
  await loadMessageBox(), Swal.fire({ title: t, text: e, icon: o });
}
let loginDialogHasLoaded = !1;
async function waitForObject(t, e, o = 5e3) {
  return new Promise((a, n) => {
    const s = Date.now(),
      i = () => {
        Date.now() - s > o
          ? n(new Error(`Timeout waiting for ${e} to load`))
          : t()
          ? a()
          : setTimeout(i, 50);
      };
    i();
  });
}
export async function initLoginDialog(t = !1) {
  if (
    (t
      ? localStorage.setItem("cryptocat_api_host", "test.riceround.online")
      : localStorage.removeItem("cryptocat_api_host"),
    !loginDialogHasLoaded)
  )
    try {
      const t = "https://cdn.staticfile.org/vue/3.2.47/vue.global.js";
      await loadResource(t, ""), await waitForObject(() => window.Vue, "vue");
      const e = "https://cdn.jsdelivr.net/npm/element-plus",
        o = "https://cdn.jsdelivr.net/npm/element-plus/dist/index.css";
      if (
        (await loadResource(e, o),
        await waitForObject(() => window.ElementPlus, "element-plus"),
        null == window.DialogLib)
      ) {
        const t = "cryptocat/static/dialog-lib.umd.cjs",
          e = "cryptocat/static/mycat.css";
        await loadResource(t, e),
          await waitForObject(() => window.DialogLib, "showLoginDialog");
      }
      loginDialogHasLoaded = !0;
    } catch (t) {
      throw t;
    }
}
function generateUUID() {
  let t = "";
  for (let e = 0; e < 32; e++) {
    t += Math.floor(16 * Math.random()).toString(16);
  }
  return t;
}
api.addEventListener("cryptocat_login_dialog", (t) => {
  const e = t.detail.client_key,
    o = t.detail.title;
  window.DialogLib.showLoginDialog({
    title: o,
    spyNetworkError: !0,
    mainKey: "cryptocat",
  })
    .then((t) => {
      api.fetchApi("/cryptocat/auth_callback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: t, client_key: e }),
      }),
        showToast("登录成功");
    })
    .catch((t) => {
      showToast("登录失败", "error");
    });
}),
  api.addEventListener("cryptocat_clear_user_info", async (t) => {
    const e = t.detail.clear_key;
    "all" == e
      ? (localStorage.removeItem("Comfy.Settings.CryptoCat.User.long_token"),
        localStorage.removeItem("cryptocat_user_token"),
        localStorage.removeItem("cryptocat_long_token"))
      : "long_token" == e
      ? (localStorage.removeItem("Comfy.Settings.CryptoCat.User.long_token"),
        localStorage.removeItem("cryptocat_long_token"))
      : "user_token" == e && localStorage.removeItem("cryptocat_user_token");
  }),
  app.registerExtension({
    name: "cryptocat.mycat",
    setup() {
      initLoginDialog();
    },
    
    async beforeRegisterNodeDef(t, e, o) {
      function setupDynamicInputs(nodeClass, width = 400) {
        const inputName = "input_anything";
        const origOnConnectionsChange = nodeClass.prototype.onConnectionsChange;

        nodeClass.prototype.onConnectionsChange = function (
          slotType,
          slot,
          connected,
          link,
          ioSlot
        ) {
          if (!link || slotType !== 1) return;

          let changed = false;

          // 删除断开连接的输入
          if (!connected && this.inputs.length > 1) {
            const stack = new Error().stack;
            if (
              !stack.includes("LGraphNode.prototype.connect") &&
              !stack.includes("LGraphNode.connect") &&
              !stack.includes("loadGraphData") &&
              this.inputs[slot].name.startsWith(inputName)
            ) {
              this.removeInput(slot);
              changed = true;
            }
          }

          // 添加新输入
          if (connected) {
            if (
              this.inputs.length === 0 ||
              (this.inputs[this.inputs.length - 1].link != null &&
                this.inputs[this.inputs.length - 1].name.startsWith(inputName))
            ) {
              const newInput =
                this.inputs.length === 0
                  ? inputName
                  : `${inputName}${this.inputs.length}`;
              this.addInput(newInput, "*");
              changed = true;
            }
          }

          // 重新编号输入
          if (changed) {
            for (let i = 0; i < this.inputs.length; i++) {
              let input = this.inputs[i];
              if (input.name.startsWith(inputName)) {
                input.name = i === 0 ? inputName : `${inputName}${i}`;
              }
            }
          }

          return origOnConnectionsChange?.apply(this, [
            slotType,
            slot,
            connected,
            link,
            ioSlot,
          ]);
        };

        // 设置节点大小
        const origOnNodeCreated = nodeClass.prototype.onNodeCreated;
        nodeClass.prototype.onNodeCreated = function () {
          const result = origOnNodeCreated
            ? origOnNodeCreated.apply(this)
            : undefined;
          if (this.size?.[0] !== undefined) {
            this.size[0] = width;
          }
          return result;
        };

        nodeClass.prototype.onResize = function (size) {
          if (size?.[0] !== undefined) {
            size[0] = width;
          }
          return size;
        };
      }

      if (
        [
          "ChenYuSaveCryptoNode",
          "ChenYuSaveLocalCryptoNode",
          "ChenYuLocalDecodeCryptoNode",
        ].includes(e.name)
      ) {
        console.log("Setting up dynamic inputs for node:", e.name);
        setupDynamicInputs(t, 400);
      }
    },
    nodeCreated(t, e) {
      if (
        ["ChenYuSaveCryptoNode", "ChenYuSaveLocalCryptoNode"].includes(
          t.comfyClass
        )
      ) {
        t.addWidget("button", "Generate UUID", "generate_uuid", () => {
          const e = generateUUID(),
            o = t.widgets.find((t) => "template_id" === t.name);
          o && (o.value = e);
        });
        t.addWidget("button", "Add Input", "add_input", () => {
          console.log(t)
          const inputName = "input_anything";
      
            const newInput =
              t.inputs.length === 0
                ? inputName
                : `${inputName}${t.inputs.length}`;
            t.addInput(newInput, "*");
          
        });
      }
    },
  });
