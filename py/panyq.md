### **盘友圈 (panyq.com) 全流程搜索API技术文档**

#### **第一部分：核心机制 — 动态 `Action ID`**

`panyq.com` 的后端API调用依赖于一种动态凭证，我们称之为 `Action ID`。这是一个40位的SHA-1哈希字符串，在API请求中作为 `next-action` HTTP头的值。

**关键特性:**

1.  **动态性**: `Action ID` 不是固定不变的。网站前端更新后，旧的ID会失效，导致API请求失败。
2.  **多样性**: 完整的搜索流程（从获取凭证到获取最终链接）需要使用 **三个不同** 的 `Action ID`，每个ID对应流程中的一个特定步骤。
3.  **来源**: 所有有效的 `Action ID` 都嵌入在网站加载的 `.js` 静态文件中。

因此，任何可靠的客户端都必须实现一套自动化的 `Action ID` 获取与验证机制，而不是硬编码这些值。

---

#### **第二部分：`Action ID` 的自动获取与验证流程**

此流程旨在从网站前端动态发现所有潜在的 `Action ID`，并通过模拟真实API调用来筛选出分别用于三个关键步骤的有效ID。

##### **流程 1: 搜寻候选 `Action ID`**

*   **目标**: 从网站的JavaScript文件中收集所有可能的 `Action ID`。
*   **步骤**:
    1.  **请求方法**: `GET`
    2.  **请求地址**: `https://panyq.com/` (网站主页)
    3.  **解析**: 从返回的HTML中，使用正则表达式 `<script src="(/_next/static/[^"]+\.js)"` 提取所有JS文件的相对路径。
    4.  **遍历请求**:
        *   对上一步找到的每个JS文件路径，拼接成完整URL (如 `https://panyq.com/_next/static/chunks/xxxx.js`) 并发起 `GET` 请求。
        *   从每个JS文件的内容中，使用正则表达式 `["']([a-f0-9]{40})["']` 提取所有40位的十六进制字符串。
    5.  **输出**: 一个包含所有潜在 `Action ID` 的集合（候选ID池）。

##### **流程 2: 顺序验证并分配 `Action ID`**

此流程按顺序验证候选ID池中的ID，并将它们分配给三个特定角色。验证一个ID后，应将其从候选池中移除，以避免重复分配。

**2.1 验证 `credential_action_id` (用于获取搜索凭证)**

*   **目标**: 找到能成功执行 **[第三部分 - 步骤1](#step1)** 的ID。
*   **验证方法**:
    *   遍历候选ID池。
    *   将当前候选ID作为 `<action_id_1>`，使用一个测试关键词（如 "test"）调用 **[步骤1: 获取搜索凭证](#step1)** API。
    *   **成功标准**: API调用成功 (HTTP状态码200) 并且响应体中能够成功解析出 `sign`, `sha`, `hash` 三个值。
    *   **结果**: 第一个满足条件的ID即为有效的 `credential_action_id`。

**2.2 验证 `intermediate_action_id` (用于执行中间步骤)**

*   **前提**: 已获得 `credential_action_id` 以及通过它获取的测试凭证 (`hash`, `sha`)。
*   **目标**: 找到能成功执行 **[第三部分 - 步骤3](#step3)** 的ID。
*   **验证方法**:
    *   遍历剩余的候选ID池。
    *   将当前候选ID作为 `<action_id_2>`，使用测试凭证和一个伪造的 `eid`（如 "fake_eid"）调用 **[步骤3: 执行中间状态确认](#step3)** API。
    *   **成功标准**: API调用成功 (HTTP状态码200)，且响应体为非空字符串。
    *   **结果**: 第一个满足条件的ID即为有效的 `intermediate_action_id`。

**2.3 验证 `final_link_action_id` (用于获取最终链接)**

*   **前提**: 已获得前两个ID及所有测试数据，包括通过 **[步骤2](#step2)** 获取的真实测试 `eid`。
*   **目标**: 找到能成功执行 **[第三部分 - 步骤4](#step4)** 的ID。
*   **验证方法**:
    *   遍历剩余的候选ID池。
    *   将当前候选ID作为 `<action_id_3>`，使用测试 `eid` 调用 **[步骤4: 获取最终链接](#step4)** API。
    *   **成功标准**: API调用成功 (HTTP状态码200)，且响应体内容包含 "http", "magnet", "aliyundrive", 或 `"url"` 等关键字。
    *   **结果**: 第一个满足条件的ID即为有效的 `final_link_action_id`。

---

### **第三部分：搜索API调用四步流程**

在成功获取并分配了三个 `Action ID` 后，即可执行标准的搜索流程。

#### **<a name="step1"></a>步骤 1: 获取搜索凭证 (Credentials)**

*   **API功能**: 根据搜索关键词获取后续API调用所需的 `sign`, `sha`, 和 `hash` 三个核心凭证。
*   **请求方法**: `POST`
*   **请求地址**: `https://panyq.com/`

*   **请求头 (Headers)**:
    ```json
    {
      "Content-Type": "text/plain;charset=UTF-8",
      "next-action": "<credential_action_id>",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
    }
    ```

*   **请求体 (Payload)**: `[{"cat": "all", "query": "<搜索关键词>", "pageNum": 1}]` (JSON字符串)

*   **关键输出 (从响应体解析)**:
    *   `sign` (字符串): 用于步骤2。
    *   `sha` (64位哈希字符串): 用于步骤3。
    *   `hash` (字符串): 用于步骤3的URL路径和请求头。

#### **<a name="step2"></a>步骤 2: 获取搜索结果列表**

*   **API功能**: 使用 `sign` 凭证，拉取包含具体资源条目的JSON列表。
*   **请求方法**: `GET`
*   **请求地址**: `https://panyq.com/api/search?sign=<sign>`

*   **请求头 (Headers)**: 仅需标准 `User-Agent`。

*   **请求体 (Payload)**: 无

*   **返回值 (Response Body)**: 包含 `data.hits` 数组的JSON对象。
    *   **关键输出**: `data.hits` 数组。每个对象最重要的字段是：
        *   `eid` (字符串): 资源的唯一标识符，用于步骤3和步骤4。
        *   `desc` (字符串), `size_str` (字符串) 等。

#### **<a name="step3"></a>步骤 3: 执行中间状态确认**

*   **API功能**: 针对每一个要获取链接的 `eid` 执行的“解锁”或“状态确认”步骤。
*   **请求方法**: `POST`
*   **请求地址**: `https://panyq.com/search/<hash>`

*   **请求头 (Headers)**:
    ```json
    {
      "Content-Type": "text/plain;charset=UTF-8",
      "next-action": "<intermediate_action_id>",
      "Referer": "https://panyq.com/search/<hash>",
      "next-router-state-tree": "<URL编码后的JSON>",
      "User-Agent": "..."
    }
    ```
    *   `next-router-state-tree` 的原始JSON: `["",{"children":["search",{"children":[["hash","<hash>","d"],{"children":["__PAGE__",{},"/search/<hash>","refresh"]}]}]},null,null,true]`

*   **请求体 (Payload)**: `[{"eid": "<eid>", "sha": "<sha>", "page_num": "1"}]` (JSON字符串)

*   **返回值**: 无需解析，但请求必须成功。

#### **<a name="step4"></a>步骤 4: 获取最终链接**

*   **API功能**: 获取可下载链接的最后一步。
*   **请求方法**: `POST`
*   **请求地址**: `https://panyq.com/go/<eid>`

*   **请求头 (Headers)**:
    ```json
    {
      "Content-Type": "text/plain;charset=UTF-8",
      "next-action": "<final_link_action_id>",
      "Referer": "https://panyq.com/go/<eid>",
      "next-router-state-tree": "<URL编码后的JSON>",
      "User-Agent": "..."
    }
    ```
    *   `next-router-state-tree` 的原始JSON: `["",{"children":["go",{"children":[["eid","<eid>","d"],{"children":["__PAGE__",{},"/go/<eid>","refresh"]}]}]},null,null,true]`

*   **请求体 (Payload)**: `[{"eid": "<eid>"}]` (JSON字符串)

*   **关键输出 (从响应体解析)**:
    *   **JSON方式**: 查找响应最后一行类似 `2:[1,{"url":"..."}]` 的结构，提取 `url` 字段。
    *   **正则方式**: 若JSON解析失败，使用正则表达式 `(https?://...|magnet:\?...)` 在整个响应文本中匹配链接。
    *   **最终结果**: 一个可用的下载链接字符串。