import base64
import json
import logging
from aiohttp import web
from database import Database
from config import PAYME_MERCHANT_ID, PAYME_TOKEN
import time
from datetime import datetime

logger = logging.getLogger(__name__)
db = Database()

def json_rpc_error(req_id, code, message, req_data=None):
    return web.json_response({
        "error": {
            "code": code,
            "message": {"uz": message, "ru": message, "en": message},
            "data": req_data
        },
        "id": req_id
    })

def get_time_ms_from_iso(iso_str):
    if not iso_str:
        return 0
    try:
        # iso parsing with fake UTC
        dt = datetime.fromisoformat(iso_str if '+' in iso_str or 'Z' in iso_str else iso_str + '+00:00')
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0

async def payme_handler(request):
    # Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        return json_rpc_error(None, -32504, "Insufficient privilege")

    encoded_cred = auth_header.split(' ')[1]
    try:
        decoded_cred = base64.b64decode(encoded_cred).decode('utf-8')
        login, password = decoded_cred.split(':', 1)
    except Exception:
        return json_rpc_error(None, -32504, "Invalid Authorization format")

    if login != 'Paycom' or password != PAYME_TOKEN:
        return json_rpc_error(None, -32504, "Insufficient privilege")
         
    try:
        req_data = await request.json()
    except Exception:
        return json_rpc_error(None, -32700, "Parse error")
        
    method = req_data.get('method')
    params = req_data.get('params', {})
    req_id = req_data.get('id')
    
    if not method:
        return json_rpc_error(req_id, -32600, "Invalid request")

    try:
        if method == "CheckPerformTransaction":
            amount = params.get('amount')
            account = params.get('account', {})
            t_id_str = account.get('order_id')
            
            if not t_id_str:
                return json_rpc_error(req_id, -31050, "Order not found", "account")
                
            try:
                t_id = int(t_id_str)
                transaction = await db.get_transaction(t_id)
            except Exception:
                return json_rpc_error(req_id, -31050, "Order not found", "account")
                
            if not transaction:
                return json_rpc_error(req_id, -31050, "Order not found", "account")
                
            expected_amount = transaction[1] * 100 
            status = transaction[2]
            
            if int(amount) != expected_amount:
                return json_rpc_error(req_id, -31001, "Incorrect amount", "amount")
                
            if status != "pending":
                return json_rpc_error(req_id, -31008, "Order is not pending")
                
            return web.json_response({
                "result": {
                    "allow": True
                },
                "id": req_id
            })

        elif method == "CreateTransaction":
            payme_t_id = params.get('id')
            time_ms = params.get('time')
            amount = params.get('amount')
            account = params.get('account', {})
            t_id_str = account.get('order_id')
            
            if not t_id_str:
                return json_rpc_error(req_id, -31050, "Order not found", "account")

            # 1-qadam: Avval shu payme_t_id bilan yaratilganmi?
            existing_tx = await db.get_transaction_by_payme_id(payme_t_id)
            if existing_tx:
                t_id_val = existing_tx[0]
                status = existing_tx[3]
                created_at = existing_tx[4]
                create_time = get_time_ms_from_iso(created_at) if get_time_ms_from_iso(created_at) else int(time.time() * 1000)
                
                if status != "pending" and status != "paid":
                    return json_rpc_error(req_id, -31008, "Transaction order cannot perform", "account")
                    
                return web.json_response({
                    "result": {
                        "create_time": create_time,
                        "transaction": str(t_id_val),
                        "state": 1 if status == "pending" else 2
                    },
                    "id": req_id
                })

            # 2-qadam: Avval yaratilmagan. Buyurtmani qidiramiz
            try:
                t_id = int(t_id_str)
                transaction = await db.get_transaction(t_id)
            except Exception:
                return json_rpc_error(req_id, -31050, "Order not found", "account")

            if not transaction:
                return json_rpc_error(req_id, -31050, "Order not found", "account")
                
            # 3-qadam: Boshqa payme_t_id bilan bandmi?
            current_payme_id = await db.get_transaction_payme_id(t_id)
                
            if current_payme_id and current_payme_id != payme_t_id:
                return json_rpc_error(req_id, -31050, "Order is attached to another transaction", "account")
                
            expected_amount = transaction[1] * 100
            status = transaction[2]
            
            if int(amount) != expected_amount:
                return json_rpc_error(req_id, -31001, "Incorrect amount", "amount")
                
            if status != "pending":
                return json_rpc_error(req_id, -31008, "Order is not pending")
                
            await db.update_transaction_payme_id(t_id, payme_t_id)
            
            fresh_tx = await db.get_transaction_by_payme_id(payme_t_id)
            created_at = fresh_tx[4] if fresh_tx else None
            create_time = get_time_ms_from_iso(created_at) if get_time_ms_from_iso(created_at) else int(time.time() * 1000)
                
            return web.json_response({
                "result": {
                    "create_time": create_time, 
                    "transaction": str(t_id_str),
                    "state": 1
                },
                "id": req_id
            })

        elif method == "PerformTransaction":
            payme_t_id = params.get('id')
            
            transaction = await db.get_transaction_by_payme_id(payme_t_id)
            if not transaction:
                return json_rpc_error(req_id, -31003, "Transaction not found")
                
            t_id = transaction[0]
            user_id = transaction[1]
            amount = transaction[2]
            status = transaction[3]
            created_at = transaction[4]
            perform_time = get_time_ms_from_iso(created_at) if get_time_ms_from_iso(created_at) else int(time.time() * 1000)

            if status == "paid":
                 return web.json_response({
                    "result": {
                        "transaction": str(t_id),
                        "perform_time": perform_time,
                        "state": 2
                    },
                    "id": req_id
                 })
                 
            if status != "pending":
                 return json_rpc_error(req_id, -31008, "Transaction cancelled or failed")

            await db.update_transaction_status(t_id, "paid")
            await db.update_balance(user_id, amount, add=True)
            new_balance = await db.get_balance(user_id)
            
            # User notification
            try:
                bot_app = request.app['bot_app']
                from keyboards import vip_tariffs_buttons
                tariffs = await db.get_vip_tariffs()
                
                await bot_app.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 Payme orqali to'lovingiz muvaffaqiyatli qabul qilindi!\n\n"
                        f"💳 Balansga qo'shildi: {amount} so'm\n"
                        f"💰 Joriy balansingiz: {new_balance} so'm\n\n"
                        f"💎 Quyidagi VIP paketlardan birini xarid qilishingiz mumkin:"
                    ),
                    reply_markup=vip_tariffs_buttons(tariffs) if tariffs else None
                )
                
                from config import ADMIN_IDS
                for admin_id in ADMIN_IDS:
                    try:
                        await bot_app.bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"💰 PAYME MERCHANT TO'LOV KELDI!\n\n"
                                f"👤 User ID: <code>{user_id}</code>\n"
                                f"📥 Buyurtma: {t_id}\n"
                                f"💵 Summa: {amount} so'm\n"
                            ),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Payme notify error: {e}")

            return web.json_response({
                "result": {
                    "transaction": str(t_id),
                    "perform_time": perform_time,
                    "state": 2
                },
                "id": req_id
            })

        elif method == "CancelTransaction":
            payme_t_id = params.get('id')
            transaction = await db.get_transaction_by_payme_id(payme_t_id)
            if not transaction:
                return json_rpc_error(req_id, -31003, "Transaction not found")
            
            t_id_val = transaction[0]
            status = transaction[3]
            created_at = transaction[4]
            cancel_time = get_time_ms_from_iso(created_at) if get_time_ms_from_iso(created_at) else int(time.time() * 1000)
            
            if status == "cancelled":
                 return web.json_response({
                     "result": {
                         "transaction": str(t_id_val),
                         "cancel_time": cancel_time,
                         "state": -1
                     },
                     "id": req_id
                 })
                 
            if status == "paid":
                 return json_rpc_error(req_id, -31007, "Transaction can not be cancelled")
                 
            await db.update_transaction_status(t_id_val, "cancelled")
            
            return web.json_response({
                "result": {
                    "transaction": str(t_id_val),
                    "cancel_time": cancel_time,
                    "state": -1
                },
                "id": req_id
            })
            
        elif method == "CheckTransaction":
            payme_t_id = params.get('id')
            transaction = await db.get_transaction_by_payme_id(payme_t_id)
            if not transaction:
                return json_rpc_error(req_id, -31003, "Transaction not found")
                
            t_id_val = transaction[0]
            status = transaction[3]
            created_at = transaction[4]
            create_time = get_time_ms_from_iso(created_at) if get_time_ms_from_iso(created_at) else int(time.time() * 1000)
            
            state = 1
            if status == "paid":
                 state = 2
            elif status == "cancelled":
                 state = -1
                 
            return web.json_response({
                "result": {
                    "create_time": create_time,
                    "perform_time": 0 if state != 2 else create_time,
                    "cancel_time": 0 if state != -1 else create_time,
                    "transaction": str(t_id_val),
                    "state": state,
                    "reason": 3 if state == -1 else None
                },
                "id": req_id
            })

        elif method == "GetStatement":
            from_ms = params.get('from', 0)
            to_ms = params.get('to', int(time.time() * 1000))
            
            rows = await db.get_transactions_by_time_range(from_ms, to_ms)
            
            transactions_list = []
            for row in rows:
                t_id, user_id, amount, status, created_at, payme_id, ts_ms = row
                state = 1
                if status == "paid":
                    state = 2
                elif status == "cancelled":
                    state = -1
                    
                transactions_list.append({
                    "id": payme_id,
                    "time": ts_ms,
                    "amount": amount * 100,
                    "account": {"order_id": str(t_id)},
                    "create_time": ts_ms,
                    "perform_time": ts_ms if state == 2 else 0,
                    "cancel_time": ts_ms if state == -1 else 0,
                    "transaction": str(t_id),
                    "state": state,
                    "reason": 3 if state == -1 else None,
                    "receivers": None
                })
            
            return web.json_response({
                "result": {
                    "transactions": transactions_list
                },
                "id": req_id
            })
            
        elif method == "ChangePassword":
            return web.json_response({
                "result": {
                    "success": True
                },
                "id": req_id
            })

        return json_rpc_error(req_id, -32601, "Method not found")

    except Exception as e:
        logger.error(f"Payme internal error: {e}", exc_info=True)
        return web.json_response({
            "error": {
                "code": -32603,
                "message": {"uz": str(e), "ru": str(e), "en": str(e)},
                "data": None
            },
            "id": req_id
        })

def init_payme_api(bot_app):
    app = web.Application()
    app['bot_app'] = bot_app
    app.router.add_post('/payme/api', payme_handler)
    return app
