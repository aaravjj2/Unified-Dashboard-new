/**
 * PyBindWrapper.cpp - Python Bindings for Institutional Engine
 * 
 * Exposes C++20 OrderBook to Python via pybind11
 * Enables high-performance LOB operations from Python strategies
 * 
 * Usage from Python:
 *   import institutional_engine as ie
 *   book = ie.OrderBook("SPY")
 *   book.add_order(1, 100.0, 100, True)  # Buy 100 @ 100.00
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "Order.h"
#include "OrderBook.h"

namespace py = pybind11;

PYBIND11_MODULE(institutional_engine, m) {
    m.doc() = R"pbdoc(
        Institutional Engine - High-Performance Limit Order Book
        ---------------------------------------------------------
        
        A C++20 matching engine with microsecond latency for
        realistic microstructure simulation.
        
        Features:
        - Price-Time Priority matching (FIFO)
        - Automatic crossed book resolution
        - >10M messages/second throughput
        - Full Python integration via pybind11
        
        Example:
            >>> import institutional_engine as ie
            >>> book = ie.OrderBook("SPY")
            >>> book.add_order(1, 100.0, 100, True)   # Buy 100 @ 100
            >>> book.add_order(2, 101.0, 50, False)   # Sell 50 @ 101
            >>> print(book.get_best_bid())            # 100.0
            >>> print(book.get_best_ask())            # 101.0
    )pbdoc";
    
    // ========================================================================
    // ENUMERATIONS
    // ========================================================================
    
    py::enum_<institutional::Side>(m, "Side", "Order side (BID/ASK)")
        .value("BID", institutional::Side::BID, "Buy order")
        .value("ASK", institutional::Side::ASK, "Sell order")
        .export_values();
    
    py::enum_<institutional::OrderType>(m, "OrderType", "Order execution type")
        .value("LIMIT", institutional::OrderType::LIMIT, "Limit order")
        .value("MARKET", institutional::OrderType::MARKET, "Market order")
        .value("IOC", institutional::OrderType::IOC, "Immediate-or-Cancel")
        .value("FOK", institutional::OrderType::FOK, "Fill-or-Kill")
        .value("POST_ONLY", institutional::OrderType::POST_ONLY, "Maker only")
        .export_values();
    
    py::enum_<institutional::OrderStatus>(m, "OrderStatus", "Order status")
        .value("NEW", institutional::OrderStatus::NEW)
        .value("PARTIALLY_FILLED", institutional::OrderStatus::PARTIALLY_FILLED)
        .value("FILLED", institutional::OrderStatus::FILLED)
        .value("CANCELLED", institutional::OrderStatus::CANCELLED)
        .value("REJECTED", institutional::OrderStatus::REJECTED)
        .export_values();
    
    // ========================================================================
    // STRUCTURES
    // ========================================================================
    
    py::class_<institutional::LimitOrder>(m, "LimitOrder", "Limit order structure")
        .def(py::init<>())
        .def(py::init<uint64_t, double, double, institutional::Side, uint64_t>(),
             py::arg("id"), py::arg("price"), py::arg("quantity"),
             py::arg("side"), py::arg("timestamp"))
        .def_readwrite("id", &institutional::LimitOrder::id)
        .def_readwrite("price", &institutional::LimitOrder::price)
        .def_readwrite("quantity", &institutional::LimitOrder::quantity)
        .def_readwrite("filled_qty", &institutional::LimitOrder::filled_qty)
        .def_readwrite("timestamp", &institutional::LimitOrder::timestamp)
        .def_readwrite("side", &institutional::LimitOrder::side)
        .def_readwrite("type", &institutional::LimitOrder::type)
        .def_readwrite("status", &institutional::LimitOrder::status)
        .def("remaining_qty", &institutional::LimitOrder::remaining_qty)
        .def("is_filled", &institutional::LimitOrder::is_filled)
        .def("is_active", &institutional::LimitOrder::is_active)
        .def("__repr__", [](const institutional::LimitOrder& o) {
            return "<LimitOrder id=" + std::to_string(o.id) + 
                   " price=" + std::to_string(o.price) +
                   " qty=" + std::to_string(o.quantity) +
                   " side=" + (o.side == institutional::Side::BID ? "BID" : "ASK") + ">";
        });
    
    py::class_<institutional::Trade>(m, "Trade", "Executed trade structure")
        .def(py::init<>())
        .def_readwrite("trade_id", &institutional::Trade::trade_id)
        .def_readwrite("buy_order_id", &institutional::Trade::buy_order_id)
        .def_readwrite("sell_order_id", &institutional::Trade::sell_order_id)
        .def_readwrite("price", &institutional::Trade::price)
        .def_readwrite("quantity", &institutional::Trade::quantity)
        .def_readwrite("timestamp", &institutional::Trade::timestamp)
        .def("__repr__", [](const institutional::Trade& t) {
            return "<Trade id=" + std::to_string(t.trade_id) +
                   " price=" + std::to_string(t.price) +
                   " qty=" + std::to_string(t.quantity) + ">";
        });
    
    py::class_<institutional::PriceLevel>(m, "PriceLevel", "Price level aggregation")
        .def(py::init<>())
        .def_readwrite("price", &institutional::PriceLevel::price)
        .def_readwrite("total_quantity", &institutional::PriceLevel::total_quantity)
        .def_readwrite("order_count", &institutional::PriceLevel::order_count)
        .def("__repr__", [](const institutional::PriceLevel& pl) {
            return "<PriceLevel price=" + std::to_string(pl.price) +
                   " qty=" + std::to_string(pl.total_quantity) +
                   " orders=" + std::to_string(pl.order_count) + ">";
        });
    
    py::class_<institutional::BookSnapshot>(m, "BookSnapshot", "Order book snapshot")
        .def(py::init<>())
        .def_readonly("bid_levels", &institutional::BookSnapshot::bid_levels)
        .def_readonly("ask_levels", &institutional::BookSnapshot::ask_levels)
        .def_readonly("timestamp", &institutional::BookSnapshot::timestamp)
        .def("get_bids", [](const institutional::BookSnapshot& snap) {
            std::vector<institutional::PriceLevel> bids;
            for (size_t i = 0; i < snap.bid_levels; i++) {
                bids.push_back(snap.bids[i]);
            }
            return bids;
        })
        .def("get_asks", [](const institutional::BookSnapshot& snap) {
            std::vector<institutional::PriceLevel> asks;
            for (size_t i = 0; i < snap.ask_levels; i++) {
                asks.push_back(snap.asks[i]);
            }
            return asks;
        });
    
    // ========================================================================
    // ORDERBOOK CLASS
    // ========================================================================
    
    py::class_<institutional::OrderBook>(m, "OrderBook", 
        R"pbdoc(
        High-Performance Limit Order Book
        
        Implements Price-Time Priority matching with automatic
        crossed book resolution.
        
        Args:
            symbol (str): Trading symbol (default: "DEFAULT")
        
        Example:
            >>> book = OrderBook("SPY")
            >>> book.add_order(1, 100.0, 100, True)   # Buy
            >>> book.add_order(2, 101.0, 50, False)   # Sell
            >>> book.get_spread()
            1.0
        )pbdoc")
        
        // Constructor
        .def(py::init<const std::string&>(),
             py::arg("symbol") = "DEFAULT",
             "Create a new order book for the given symbol")
        
        // Core operations
        .def("add_order", &institutional::OrderBook::add_order,
             py::arg("id"), py::arg("price"), py::arg("quantity"), py::arg("is_buy"),
             R"pbdoc(
             Add a new order to the book.
             
             CRITICAL: If order crosses the spread, it matches immediately.
             
             Args:
                 id (int): Unique order identifier
                 price (float): Limit price
                 quantity (float): Order quantity
                 is_buy (bool): True for buy (BID), False for sell (ASK)
             
             Returns:
                 int: Order ID if accepted, 0 if rejected
             )pbdoc")
        
        .def("cancel_order", &institutional::OrderBook::cancel_order,
             py::arg("id"),
             "Cancel an existing order by ID. Returns True if found and cancelled.")
        
        .def("modify_order", &institutional::OrderBook::modify_order,
             py::arg("id"), py::arg("new_price"), py::arg("new_quantity"),
             "Modify an order (cancel + replace). Loses time priority.")
        
        // Market data
        .def("get_best_bid", [](const institutional::OrderBook& book) -> py::object {
                auto bid = book.get_best_bid();
                if (bid) return py::cast(*bid);
                return py::none();
             },
             "Get best bid price, or None if no bids")
        
        .def("get_best_ask", [](const institutional::OrderBook& book) -> py::object {
                auto ask = book.get_best_ask();
                if (ask) return py::cast(*ask);
                return py::none();
             },
             "Get best ask price, or None if no asks")
        
        .def("get_best_bid_qty", &institutional::OrderBook::get_best_bid_qty,
             "Get total quantity at best bid")
        
        .def("get_best_ask_qty", &institutional::OrderBook::get_best_ask_qty,
             "Get total quantity at best ask")
        
        .def("get_spread", &institutional::OrderBook::get_spread,
             "Get bid-ask spread, or -1 if book is empty")
        
        .def("get_mid_price", &institutional::OrderBook::get_mid_price,
             "Get mid price (bid + ask) / 2, or -1 if book is empty")
        
        .def("get_snapshot", &institutional::OrderBook::get_snapshot,
             py::arg("levels") = 5,
             "Get order book snapshot (top N levels)")
        
        .def("get_snapshot_json", &institutional::OrderBook::get_snapshot_json,
             py::arg("levels") = 5,
             "Get order book snapshot as JSON string")
        
        // Statistics
        .def("get_order_count", &institutional::OrderBook::get_order_count,
             "Get total number of active orders")
        
        .def("get_bid_level_count", &institutional::OrderBook::get_bid_level_count,
             "Get number of bid price levels")
        
        .def("get_ask_level_count", &institutional::OrderBook::get_ask_level_count,
             "Get number of ask price levels")
        
        .def("get_total_bid_volume", &institutional::OrderBook::get_total_bid_volume,
             "Get total volume on bid side")
        
        .def("get_total_ask_volume", &institutional::OrderBook::get_total_ask_volume,
             "Get total volume on ask side")
        
        .def("get_trade_count", &institutional::OrderBook::get_trade_count,
             "Get total number of trades executed")
        
        .def("get_traded_volume", &institutional::OrderBook::get_traded_volume,
             "Get total volume traded")
        
        .def("get_symbol", &institutional::OrderBook::get_symbol,
             "Get trading symbol")
        
        .def("get_recent_trades", &institutional::OrderBook::get_recent_trades,
             py::arg("count") = 10,
             "Get recent trades (up to last 1000)")
        
        // Utility
        .def("clear", &institutional::OrderBook::clear,
             "Clear all orders from the book")
        
        .def("__repr__", [](const institutional::OrderBook& book) {
            auto bid = book.get_best_bid();
            auto ask = book.get_best_ask();
            std::string bid_str = bid ? std::to_string(*bid) : "None";
            std::string ask_str = ask ? std::to_string(*ask) : "None";
            return "<OrderBook symbol=" + book.get_symbol() +
                   " bid=" + bid_str + " ask=" + ask_str +
                   " orders=" + std::to_string(book.get_order_count()) + ">";
        });
    
    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================
    
    m.def("get_timestamp_ns", &institutional::get_timestamp_ns,
          "Get current timestamp in nanoseconds");
    
    m.def("round_to_tick", &institutional::round_to_tick,
          py::arg("price"), py::arg("tick_size") = institutional::TICK_SIZE_EQUITY,
          "Round price to the nearest tick size");
    
    m.def("validate_order", &institutional::validate_order,
          py::arg("price"), py::arg("quantity"),
          "Validate order parameters");
    
    // Constants
    m.attr("TICK_SIZE_EQUITY") = institutional::TICK_SIZE_EQUITY;
    m.attr("TICK_SIZE_OPTION_SMALL") = institutional::TICK_SIZE_OPTION_SMALL;
    m.attr("TICK_SIZE_OPTION_LARGE") = institutional::TICK_SIZE_OPTION_LARGE;
    m.attr("MIN_ORDER_QTY") = institutional::MIN_ORDER_QTY;
    m.attr("MAX_PRICE") = institutional::MAX_PRICE;
    
    // Version
    m.attr("__version__") = "1.0.0";
}





