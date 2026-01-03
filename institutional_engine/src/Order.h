/**
 * Order.h - Institutional-Grade Order Structures
 * 
 * High-Performance Limit Order Book (LOB) Data Types
 * Designed for microsecond-level simulation accuracy
 * 
 * Architecture: C++20 with constexpr optimizations
 * Memory Model: POD structures for cache efficiency
 */

#ifndef INSTITUTIONAL_ENGINE_ORDER_H
#define INSTITUTIONAL_ENGINE_ORDER_H

#include <cstdint>
#include <string>
#include <chrono>

namespace institutional {

// ============================================================================
// CONSTANTS - Compile-time Tick Sizes
// ============================================================================

/// Standard equity tick size (US markets)
constexpr double TICK_SIZE_EQUITY = 0.01;

/// Options tick size (sub-$3 options)
constexpr double TICK_SIZE_OPTION_SMALL = 0.05;

/// Options tick size (>$3 options)
constexpr double TICK_SIZE_OPTION_LARGE = 0.10;

/// Minimum order quantity
constexpr double MIN_ORDER_QTY = 1.0;

/// Maximum price (sanity check)
constexpr double MAX_PRICE = 1000000.0;

// ============================================================================
// ENUMERATIONS
// ============================================================================

/**
 * Order Side - Bid (Buy) or Ask (Sell)
 */
enum class Side : uint8_t {
    BID = 0,  // Buy order
    ASK = 1   // Sell order
};

/**
 * Order Type - Execution instructions
 */
enum class OrderType : uint8_t {
    LIMIT = 0,      // Limit order - wait in book
    MARKET = 1,     // Market order - immediate execution
    IOC = 2,        // Immediate-or-Cancel
    FOK = 3,        // Fill-or-Kill
    POST_ONLY = 4   // Maker-only (reject if would take)
};

/**
 * Order Status - Current state of order
 */
enum class OrderStatus : uint8_t {
    NEW = 0,           // Just created
    PARTIALLY_FILLED = 1,
    FILLED = 2,
    CANCELLED = 3,
    REJECTED = 4
};

// ============================================================================
// STRUCTURES
// ============================================================================

/**
 * LimitOrder - Core order representation
 * 
 * Memory Layout: 48 bytes (aligned for cache efficiency)
 * All fields use fixed-width types for deterministic behavior
 */
struct LimitOrder {
    uint64_t id;              // Unique order identifier
    double price;             // Limit price
    double quantity;          // Original quantity
    double filled_qty;        // Quantity already filled
    uint64_t timestamp;       // Nanosecond timestamp (epoch)
    Side side;                // BID or ASK
    OrderType type;           // Order type
    OrderStatus status;       // Current status
    
    // Padding for alignment (explicit)
    uint8_t _padding[5];
    
    /**
     * Default constructor - zero-initialized
     */
    constexpr LimitOrder() noexcept
        : id(0), price(0.0), quantity(0.0), filled_qty(0.0),
          timestamp(0), side(Side::BID), type(OrderType::LIMIT),
          status(OrderStatus::NEW), _padding{} {}
    
    /**
     * Parameterized constructor
     */
    constexpr LimitOrder(uint64_t order_id, double order_price, 
                         double order_qty, Side order_side,
                         uint64_t order_timestamp) noexcept
        : id(order_id), price(order_price), quantity(order_qty),
          filled_qty(0.0), timestamp(order_timestamp), side(order_side),
          type(OrderType::LIMIT), status(OrderStatus::NEW), _padding{} {}
    
    /**
     * Get remaining (unfilled) quantity
     */
    [[nodiscard]] constexpr double remaining_qty() const noexcept {
        return quantity - filled_qty;
    }
    
    /**
     * Check if order is fully filled
     */
    [[nodiscard]] constexpr bool is_filled() const noexcept {
        return filled_qty >= quantity;
    }
    
    /**
     * Check if order is active (can be matched)
     */
    [[nodiscard]] constexpr bool is_active() const noexcept {
        return status == OrderStatus::NEW || 
               status == OrderStatus::PARTIALLY_FILLED;
    }
};

/**
 * Trade - Represents an executed trade
 */
struct Trade {
    uint64_t trade_id;        // Unique trade identifier
    uint64_t buy_order_id;    // Aggressor or passive buy
    uint64_t sell_order_id;   // Aggressor or passive sell
    double price;             // Execution price
    double quantity;          // Executed quantity
    uint64_t timestamp;       // Execution timestamp
    
    constexpr Trade() noexcept
        : trade_id(0), buy_order_id(0), sell_order_id(0),
          price(0.0), quantity(0.0), timestamp(0) {}
    
    constexpr Trade(uint64_t tid, uint64_t buy_id, uint64_t sell_id,
                    double exec_price, double exec_qty, uint64_t ts) noexcept
        : trade_id(tid), buy_order_id(buy_id), sell_order_id(sell_id),
          price(exec_price), quantity(exec_qty), timestamp(ts) {}
};

/**
 * PriceLevel - Aggregated view of orders at a price
 */
struct PriceLevel {
    double price;
    double total_quantity;
    uint32_t order_count;
    
    constexpr PriceLevel() noexcept
        : price(0.0), total_quantity(0.0), order_count(0) {}
    
    constexpr PriceLevel(double p, double qty, uint32_t cnt) noexcept
        : price(p), total_quantity(qty), order_count(cnt) {}
};

/**
 * BookSnapshot - Top N levels of the order book
 */
struct BookSnapshot {
    static constexpr size_t MAX_LEVELS = 10;
    
    PriceLevel bids[MAX_LEVELS];
    PriceLevel asks[MAX_LEVELS];
    size_t bid_levels;
    size_t ask_levels;
    uint64_t timestamp;
    
    constexpr BookSnapshot() noexcept
        : bids{}, asks{}, bid_levels(0), ask_levels(0), timestamp(0) {}
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get current timestamp in nanoseconds
 */
inline uint64_t get_timestamp_ns() {
    auto now = std::chrono::high_resolution_clock::now();
    auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
        now.time_since_epoch());
    return static_cast<uint64_t>(ns.count());
}

/**
 * Round price to tick size
 */
constexpr double round_to_tick(double price, double tick_size = TICK_SIZE_EQUITY) {
    return static_cast<int64_t>(price / tick_size + 0.5) * tick_size;
}

/**
 * Validate order parameters
 */
constexpr bool validate_order(double price, double qty) noexcept {
    return price > 0.0 && price < MAX_PRICE && 
           qty >= MIN_ORDER_QTY;
}

/**
 * Side to string conversion
 */
inline std::string side_to_string(Side side) {
    return side == Side::BID ? "BID" : "ASK";
}

/**
 * Status to string conversion
 */
inline std::string status_to_string(OrderStatus status) {
    switch (status) {
        case OrderStatus::NEW: return "NEW";
        case OrderStatus::PARTIALLY_FILLED: return "PARTIAL";
        case OrderStatus::FILLED: return "FILLED";
        case OrderStatus::CANCELLED: return "CANCELLED";
        case OrderStatus::REJECTED: return "REJECTED";
        default: return "UNKNOWN";
    }
}

} // namespace institutional

#endif // INSTITUTIONAL_ENGINE_ORDER_H





