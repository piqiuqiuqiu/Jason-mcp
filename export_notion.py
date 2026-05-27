import sys,json,asyncio
sys.path.insert(0,"/app/server/tools")
from notion2word import handle as notion2word
from notion_fetch import handle as notion_fetch
async def main():
    r1=await notion_fetch({"page_id":"e0e073a7056f4a0c97d9e2cc80feee4f","format":"markdown"})
    d=json.loads(r1)
    if d["status"]!="SUCCESS":
        print("FETCH_FAILED");return
    r2=await notion2word({"markdown":d["markdown"],"output":"/app/files/doc_e0e073a7_20260413_141000.docx","title":d.get("title","")})
    print(r2)
asyncio.run(main())