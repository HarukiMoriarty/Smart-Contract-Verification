Eleven has its own token called 11nrvbusd, but it use ERC20 as basic token.
In normal withdrawn, Eleven should return back the ERC20, and clear the balanceof[client], so that the client should have no 11nrvbusd.
However, `emergencyburn` do not do the clearance, so that the client can still call another `withdrawnAll`.