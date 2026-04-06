#include <crow.h>
#include <crow/http_request.h>
#include <cstdint>
#include <cstdlib>
#include <string>

#include "generated/pages.hpp"

// helper - every page route goes through this
template<std::size_t N>
crow::response html_response(const fixed_string<N>& page)
{
    crow::response res{ 200, std::string(page.sv()) };
    res.set_header("Content-Type",    "text/html; charset=utf-8");
    res.set_header("X-Frame-Options", "DENY");
    res.set_header("Content-Security-Policy",
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'none';");
    return res;
}

int main()
{
    crow::SimpleApp app;

    CROW_ROUTE(app, "/"             )([]() { return html_response(portfolio::pages::index);         });
    CROW_ROUTE(app, "/about"        )([]() { return html_response(portfolio::pages::about);         });
    CROW_ROUTE(app, "/projects"     )([]() { return html_response(portfolio::pages::projects);      });
    CROW_ROUTE(app, "/contact"      )([]() { return html_response(portfolio::pages::contact);       });
    CROW_ROUTE(app, "/resume"       )([]() { return html_response(portfolio::pages::resume);        });
    CROW_ROUTE(app, "/uses"         )([]() { return html_response(portfolio::pages::uses);          });
    CROW_ROUTE(app, "/now"          )([]() { return html_response(portfolio::pages::now);           });
    CROW_ROUTE(app, "/testimonials" )([]() { return html_response(portfolio::pages::testimonials);  });
    CROW_ROUTE(app, "/hire"         )([]() { return html_response(portfolio::pages::hire);          });
    CROW_ROUTE(app, "/changelog"    )([]() { return html_response(portfolio::pages::changelog);     });
    CROW_ROUTE(app, "/explore"      )([]() { return html_response(portfolio::pages::explore);       });

    CROW_ROUTE(app, "/healthz")([]() {
        return crow::response{200, "ok"};
    });

    app.route_dynamic("/<path>")(
        [](const crow::request&, crow::response& res, std::string) {
            res = html_response(portfolio::pages::not_found);
            res.code = 404;
            res.end();
        }
    );

    const char*    port_env = std::getenv("PORT");
    const uint16_t port     = port_env
        ? static_cast<uint16_t>(std::stoi(port_env))
        : 8080;

    app.loglevel(crow::LogLevel::Info)
       .port(port)
       .multithreaded()
       .run();
}
